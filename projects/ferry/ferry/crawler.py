"""Single-origin breadth-first crawling with a transactional, resumable frontier."""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import http.client
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .archive import Archive, writer_lock
from .core import USER_AGENT, Robots, extract, normalize_url, origin


class BlockedURL(ValueError):
    pass


class SkipResponse(ValueError):
    pass


class Redirects(HTTPRedirectHandler):
    def __init__(self, guard, before_request):
        self.guard = guard
        self.before_request = before_request

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        normalized = normalize_url(newurl, req.full_url)
        reason = self.guard(normalized)
        if reason:
            raise BlockedURL(f"重定向被拦截：{reason}")
        redirect = super().redirect_request(req, fp, code, msg, headers, normalized)
        if redirect is not None:
            self.before_request()
        return redirect


@dataclass
class Response:
    body: bytes
    url: str
    status: int
    mime: str
    charset: str | None


class Crawler:
    def __init__(self, archive: Archive, progress=None):
        self.archive = archive
        self.config = archive.config
        self.site = origin(self.config["seed"])
        self.include = re.compile(self.config["include"]) if self.config["include"] else None
        self.exclude = re.compile(self.config["exclude"]) if self.config["exclude"] else None
        self.robots = Robots()
        self.robots_loaded = False
        self.delay = self.config["delay"]
        self.last_request = 0.0
        self.progress = progress
        self.opener = build_opener(Redirects(self.guard, self.before_request))

    def guard(self, url: str | None) -> str:
        if not url:
            return "非 HTTP(S) 网址或网址无效"
        if origin(url) != self.site:
            return "超出起始站点（协议、域名、端口必须相同）"
        if not self.robots_loaded:
            return ""
        if self.exclude and self.exclude.search(url):
            return "命中 exclude 规则"
        if self.include and url != self.config["seed"] and not self.include.search(url):
            return "未命中 include 规则"
        if not self.robots.allows(url):
            return "robots.txt 禁止采集"
        return ""

    def before_request(self):
        remaining = self.delay - (time.monotonic() - self.last_request)
        if remaining > 0:
            time.sleep(remaining)
        self.last_request = time.monotonic()

    def fetch(self, url: str, *, robots=False) -> Response:
        self.before_request()
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity",
                                      "Accept": "text/html,text/plain,application/xhtml+xml,application/json;q=0.8,*/*;q=0.1"})
        with self.opener.open(request, timeout=self.config["timeout"]) as response:
            mime = response.headers.get_content_type()
            if not robots and not (mime.startswith("text/") or mime in (
                    "application/xhtml+xml", "application/json", "application/xml")):
                raise SkipResponse(f"不支持的内容类型：{mime}")
            limit = 512 * 1024 if robots else self.config["max_bytes"]
            length = response.headers.get("Content-Length", "")
            if length.isdigit() and int(length) > limit:
                raise SkipResponse(f"响应超过单页上限 {limit} 字节")
            encoding = response.headers.get("Content-Encoding", "identity").lower().strip()
            if encoding == "gzip":
                with gzip.GzipFile(fileobj=response) as stream:
                    body = stream.read(limit + 1)
            elif encoding in ("identity", ""):
                body = response.read(limit + 1)
            else:
                raise SkipResponse(f"不支持的传输压缩：{encoding}")
            if len(body) > limit:
                raise SkipResponse(f"响应超过单页上限 {limit} 字节")
            if encoding in ("identity", "") and length.isdigit() and len(body) != int(length):
                raise OSError("响应提前断开，未保存不完整内容")
            return Response(body, response.url, response.status, mime, response.headers.get_content_charset())

    def load_robots(self):
        try:
            response = self.fetch(self.site + "/robots.txt", robots=True)
            body = response.body.decode("utf-8-sig", errors="replace")
        except HTTPError as exc:
            if exc.code in (401, 403):
                body = "User-agent: *\nDisallow: /"
            elif 400 <= exc.code < 500 and exc.code != 429:
                body = ""
            else:
                raise ValueError(f"robots.txt 返回 HTTP {exc.code}，本次停止，可稍后 resume") from exc
        except (OSError, URLError, ValueError, EOFError, http.client.HTTPException) as exc:
            raise ValueError(f"无法确认 robots.txt，尚未采集页面：{exc}") from exc
        self.robots = Robots(body)
        self.robots_loaded = True
        self.delay = max(self.delay, self.robots.delay)
        self.archive.set_meta("robots", body)

    def discover(self, page: dict, links: list[str]):
        db = self.archive.db
        count = db.execute("SELECT count(*) FROM pages").fetchone()[0]
        for url in links:
            if origin(url) != self.site:
                decision = "external"
            elif self.guard(url):
                decision = "policy"
            elif page["depth"] >= self.config["depth"]:
                decision = "depth"
            elif db.execute("SELECT 1 FROM pages WHERE url=?", (url,)).fetchone():
                decision = "known"
            elif count >= self.config["max_queue"]:
                decision = "queue-limit"
            else:
                db.execute("INSERT INTO pages(url,depth,parent) VALUES (?,?,?)",
                           (url, page["depth"] + 1, page["url"]))
                count += 1
                decision = "queued"
            db.execute("INSERT OR REPLACE INTO links VALUES (?,?,?)", (page["url"], url, decision))

    def run(self, max_pages: int, *, retry_errors=False) -> dict:
        with writer_lock(self.archive.root):
            self.load_robots()
            db = self.archive.db
            if retry_errors:
                db.execute("UPDATE pages SET state='pending',reason='' WHERE state='error'")
                db.commit()
            attempted = 0
            while attempted < max_pages:
                row = db.execute("SELECT * FROM pages WHERE state='pending' ORDER BY depth,id LIMIT 1").fetchone()
                if row is None:
                    break
                page = dict(row)
                reason = self.guard(page["url"])
                if reason:
                    self.archive.finish(page["id"], state="blocked", reason=reason)
                    db.commit()
                    if self.progress:
                        self.progress(page["url"], "blocked", reason)
                    continue
                attempted += 1
                try:
                    db.execute("UPDATE pages SET attempts=attempts+1 WHERE id=?", (page["id"],))
                    response = self.fetch(page["url"])
                    document = extract(response.body, response.url, response.mime, response.charset)
                    terms = self.config["contains"].casefold().split()
                    haystack = (document.title + "\n" + document.text).casefold()
                    keep = all(term in haystack for term in terms)
                    digest = self.archive.save_object(response.body) if keep else None
                    state = "saved" if keep else "filtered"
                    reason = "" if keep else "标题/正文未同时包含 contains 的所有关键词"
                    if document.links_truncated:
                        reason += ("；" if reason else "") + "链接超过 2000 个，仅提取前 2000 个"
                    self.archive.finish(page["id"], state=state, status=response.status,
                                        final_url=response.url, title=document.title,
                                        text=document.text if keep else "", mime=response.mime,
                                        sha256=digest, bytes=len(response.body), reason=reason)
                    self.discover(page, document.links)
                    db.commit()
                except KeyboardInterrupt:
                    db.rollback()
                    raise
                except (HTTPError, URLError, OSError, ValueError, EOFError, http.client.HTTPException) as exc:
                    db.rollback()
                    state = "blocked" if isinstance(exc, BlockedURL) else "skipped" if isinstance(exc, SkipResponse) else "error"
                    reason = f"HTTP {exc.code}" if isinstance(exc, HTTPError) else str(exc)
                    db.execute("UPDATE pages SET attempts=attempts+1 WHERE id=?", (page["id"],))
                    self.archive.finish(page["id"], state=state, reason=reason,
                                        status=exc.code if isinstance(exc, HTTPError) else None)
                    db.commit()
                if self.progress:
                    self.progress(page["url"], state, reason)
            result = self.archive.stats()
            result["attempted_this_run"] = attempted
            return result
