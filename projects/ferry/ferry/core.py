"""URL identity, readable HTML extraction, and robots policy; no browser required."""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

USER_AGENT = "Ferry/0.1 (+local-first website archiver)"
MAX_LINKS = 2000


def normalize_url(url: str, base: str = "") -> str | None:
    """HTTP(S) only; remove fragments, retain meaningful query order and values."""
    try:
        if any(ord(c) < 32 or ord(c) == 127 for c in url):
            return None
        url = urljoin(base, url.strip())
        parts = urlsplit(url)
        if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if ":" in host:
            host = f"[{host}]"
        port = parts.port
        if port is not None and port != {"http": 80, "https": 443}[parts.scheme.lower()]:
            host += f":{port}"
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        query = quote(parts.query, safe="%/:?@!$&'()*+,;=-._~[]")
        return urlunsplit((parts.scheme.lower(), host, path, query, ""))
    except (ValueError, UnicodeError):
        return None


def origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def decode_body(raw: bytes, charset: str | None) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")
    meta = re.search(br'<meta\b[^>]*charset\s*=\s*[\'\"]?\s*([a-zA-Z0-9_-]+)', raw[:8192], re.I)
    for candidate in (charset, meta.group(1).decode("ascii") if meta else None, "utf-8", "gb18030"):
        if candidate:
            try:
                return raw.decode(candidate)
            except (UnicodeError, LookupError):
                pass
    return raw.decode("utf-8", errors="replace")


@dataclass
class Document:
    title: str
    text: str
    links: list[str]
    links_truncated: bool = False


class Extractor(HTMLParser):
    BLOCKS = {"p", "div", "section", "article", "main", "header", "footer", "nav", "li",
              "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "pre", "blockquote"}
    HIDDEN = {"script", "style", "template", "noscript"}

    def __init__(self, url: str):
        super().__init__(convert_charrefs=True)
        self.url, self.base = url, url
        self.base_seen = False
        self.hidden: list[str] = []
        self.in_title = False
        self.title_parts: list[str] = []
        self.parts: list[str] = []
        self.raw_links: list[str] = []
        self.links_truncated = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in self.HIDDEN:
            self.hidden.append(tag)
        if self.hidden:
            return
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag in ("td", "th"):
            self.parts.append("\t")
        if tag == "a":
            self.parts.append(" ")
        if tag == "base" and attrs.get("href") and not self.base_seen:
            self.base = normalize_url(attrs["href"], self.url) or self.url
            self.base_seen = True
        if tag == "a" and attrs.get("href"):
            if len(self.raw_links) < MAX_LINKS:
                self.raw_links.append(attrs["href"])
            else:
                self.links_truncated = True
        if tag == "img" and attrs.get("alt"):
            self.parts.append(f" {attrs['alt']} ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.hidden:
            if tag in self.hidden:
                index = len(self.hidden) - 1 - self.hidden[::-1].index(tag)
                del self.hidden[index:]
            return
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "a":
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            if self.in_title:
                self.title_parts.append(data)
            else:
                self.parts.append(data)

    def document(self) -> Document:
        lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        text = "\n".join(line for line in lines if line)
        links = list(dict.fromkeys(u for link in self.raw_links
                                   if (u := normalize_url(link, self.base))))
        return Document(" ".join("".join(self.title_parts).split()), text, links, self.links_truncated)


def extract(raw: bytes, url: str, mime: str, charset: str | None) -> Document:
    text = decode_body(raw, charset)
    if mime not in ("text/html", "application/xhtml+xml"):
        return Document(urlsplit(url).path.rsplit("/", 1)[-1] or url, text.strip(), [])
    parser = Extractor(url)
    parser.feed(text)
    parser.close()
    return parser.document()


def robots_path(value: str) -> str:
    value = quote(value, safe="/%?=&:;+$,!@'()[]*~-._")
    def replace(match):
        char = chr(int(match.group(0)[1:], 16))
        return char if re.fullmatch(r"[a-zA-Z0-9._~-]", char) else match.group(0).upper()
    return re.sub(r"%[0-9a-fA-F]{2}", replace, value)


class Robots:
    """Most-specific agent group; longest path match, Allow ties, * and $ support."""
    def __init__(self, body: str = ""):
        groups = []
        agents, rules, delay, has_rules = [], [], 0.0, False
        for line in body.splitlines() + ["User-agent: __end__"]:
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (p.strip() for p in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if has_rules:
                    groups.append((agents, rules, delay))
                    agents, rules, delay, has_rules = [], [], 0.0, False
                agents.append(value.lower())
            elif agents and key in ("allow", "disallow", "crawl-delay"):
                has_rules = True
                if key == "crawl-delay":
                    try:
                        number = float(value)
                        if 0 <= number <= 86400:
                            delay = number
                    except ValueError:
                        pass
                elif value:
                    rules.append((robots_path(value), key == "allow"))
        ranked = []
        for agents, rules, delay in groups:
            scores = [len(a) if a != "*" else 0 for a in agents if a == "*" or a in "ferry"]
            if scores:
                ranked.append((max(scores), rules, delay))
        best = max((g[0] for g in ranked), default=-1)
        self.rules = [r for score, rules, _ in ranked if score == best for r in rules]
        self.delay = max((d for score, _, d in ranked if score == best), default=0)

    def allows(self, url: str) -> bool:
        p = urlsplit(url)
        path = robots_path(p.path + ("?" + p.query if p.query else ""))
        matches = []
        for pattern, allow in self.rules:
            anchored = pattern.endswith("$")
            value = pattern[:-1] if anchored else pattern
            expression = "^" + re.escape(value).replace(r"\*", ".*") + ("$" if anchored else "")
            if re.search(expression, path):
                matches.append((len(value.replace("*", "")), allow))
        return max(matches)[1] if matches else True
