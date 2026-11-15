"""Durable frontier + content-addressed bodies, with offline querying and audit."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

SCHEMA = "1"
STATES = ("pending", "saved", "filtered", "blocked", "skipped", "error")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def writer_lock(root: Path):
    """OS releases the advisory lock even after a crash. Keep the lock inode stable."""
    import fcntl
    with (root / ".writer.lock").open("a+b") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("该档案已有采集进程，请等待它完成") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class Archive:
    def __init__(self, root: Path, *, config: dict | None = None):
        self.root = root.absolute()
        self.db = None
        if config is not None:
            self.root.mkdir(parents=True, exist_ok=False)
            (self.root / "objects").mkdir()
        elif not (self.root / "archive.sqlite3").is_file():
            raise ValueError(f"找不到拾页档案：{self.root}")
        self.db = sqlite3.connect(self.root / "archive.sqlite3", timeout=5)
        self.db.row_factory = sqlite3.Row
        if config is not None:
            self.db.executescript("""
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE pages (
                    id INTEGER PRIMARY KEY, url TEXT NOT NULL UNIQUE, depth INTEGER NOT NULL,
                    parent TEXT, state TEXT NOT NULL DEFAULT 'pending',
                    status INTEGER, final_url TEXT, title TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL DEFAULT '', mime TEXT, sha256 TEXT,
                    bytes INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '',
                    fetched_at TEXT, attempts INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE links (
                    parent TEXT NOT NULL, url TEXT NOT NULL, decision TEXT NOT NULL,
                    PRIMARY KEY(parent, url)
                );
                CREATE INDEX pages_state ON pages(state, depth, id);
            """)
            self.db.executemany("INSERT INTO meta VALUES (?,?)", [
                ("schema", SCHEMA), ("created_at", now()), ("config", json.dumps(config, ensure_ascii=False))])
            self.db.execute("INSERT INTO pages(url,depth) VALUES (?,0)", (config["seed"],))
            self.db.commit()
        try:
            if self.meta("schema") != SCHEMA:
                raise ValueError("不支持的档案版本")
            self.config = json.loads(self.meta("config"))
        except (sqlite3.Error, TypeError, json.JSONDecodeError):
            self.close()
            raise ValueError("档案数据库损坏或格式不正确") from None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None

    def meta(self, key):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))
        self.db.commit()

    def object_path(self, digest: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("无效的内容指纹")
        path = self.root / "objects" / digest[:2] / (digest + ".raw")
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("档案中的对象路径越出了档案目录")
        return path

    def save_object(self, body: bytes) -> str:
        digest = hashlib.sha256(body).hexdigest()
        target = self.object_path(digest)
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() == digest:
                return digest
            raise ValueError(f"已有对象损坏，请先运行 verify：{digest}")
        fd, temporary = tempfile.mkstemp(prefix=".incoming-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return digest

    def finish(self, page_id: int, **fields):
        allowed = {"state", "status", "final_url", "title", "text", "mime", "sha256", "bytes", "reason"}
        if not fields.keys() <= allowed:
            raise ValueError("未知的页面字段")
        fields["fetched_at"] = now()
        assignments = ",".join(f"{name}=?" for name in fields)
        self.db.execute(f"UPDATE pages SET {assignments} WHERE id=?", (*fields.values(), page_id))
        # The caller commits this together with discovered links, so interruption cannot lose a frontier.

    def iter_rows(self):
        for row in self.db.execute("SELECT * FROM pages ORDER BY id"):
            yield dict(row)

    def rows(self) -> list[dict]:
        return list(self.iter_rows())

    def stats(self) -> dict:
        counts = {s: 0 for s in STATES}
        counts.update(dict(self.db.execute("SELECT state,count(*) FROM pages GROUP BY state")))
        objects = self.db.execute("SELECT count(DISTINCT sha256),coalesce(sum(bytes),0) FROM pages WHERE state='saved'").fetchone()
        unique_bytes = self.db.execute("SELECT coalesce(sum(n),0) FROM (SELECT max(bytes) n FROM pages WHERE state='saved' GROUP BY sha256)").fetchone()[0]
        return {"archive": str(self.root), "seed": self.config["seed"], "created_at": self.meta("created_at"),
                "counts": counts, "objects": objects[0], "page_bytes": objects[1],
                "stored_bytes": unique_bytes, "deduplicated_bytes": objects[1] - unique_bytes,
                "links": dict(self.db.execute("SELECT decision,count(*) FROM links GROUP BY decision")),
                "config": self.config}

    def verify(self) -> list[dict]:
        issues = []
        check = self.db.execute("PRAGMA integrity_check").fetchall()
        for row in check:
            if row[0] != "ok":
                issues.append({"sha256": None, "reason": row[0]})
        for row in self.db.execute("SELECT DISTINCT sha256,bytes FROM pages WHERE state='saved'"):
            digest, expected_size = row
            try:
                path = self.object_path(digest)
                actual = hashlib.sha256()
                size = 0
                with path.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        actual.update(chunk)
                        size += len(chunk)
                if actual.hexdigest() != digest or size != expected_size:
                    issues.append({"sha256": digest, "reason": "内容指纹或大小不符"})
            except (OSError, ValueError, TypeError) as exc:
                issues.append({"sha256": digest, "reason": str(exc)})
        return issues


def select_pages(rows: list[dict], *, query="", url="", title="", state="saved", min_chars=0, limit=0) -> list[dict]:
    url_re = re.compile(url, re.I) if url else None
    title_re = re.compile(title, re.I) if title else None
    terms = query.casefold().split()
    states = set(state.split(",")) if state != "all" else set()
    if states - set(STATES):
        raise ValueError(f"未知状态：{', '.join(sorted(states - set(STATES)))}")
    result = []
    for row in rows:
        if states and row["state"] not in states:
            continue
        if url_re and not url_re.search(row["url"]):
            continue
        if title_re and not title_re.search(row["title"]):
            continue
        text = (row["title"] + "\n" + row["text"]).casefold()
        if not all(term in text for term in terms) or len(row["text"]) < min_chars:
            continue
        result.append(row)
        if limit and len(result) >= limit:
            break
    return result
