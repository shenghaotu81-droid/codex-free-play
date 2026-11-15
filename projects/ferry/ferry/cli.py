from __future__ import annotations

import argparse
import csv
from datetime import datetime
import io
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile

from . import __version__
from .archive import Archive, select_pages
from .core import normalize_url
from .crawler import Crawler
from .view import banner, browse, results, safe, summary


def positive(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return n


def nonnegative(value):
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError("不能小于 0")
    return n


def duration(value):
    n = float(value)
    if not 0 <= n <= 3600:
        raise argparse.ArgumentTypeError("必须在 0 到 3600 秒之间")
    return n


def filters(parser, *, limit=False):
    parser.add_argument("query", nargs="?", default="", help="标题/正文关键词，空格分隔且全部匹配")
    parser.add_argument("--url", default="", help="网址正则表达式")
    parser.add_argument("--title", default="", help="标题正则表达式")
    parser.add_argument("--state", default="saved", help="saved / pending / error / filtered / blocked / skipped / all；可逗号分隔")
    parser.add_argument("--min-chars", type=nonnegative, default=0, help="正文最少字符数")
    parser.add_argument("--limit", type=nonnegative, default=20 if limit else 0, help="最多返回多少条；0 表示全部")


def parser():
    p = argparse.ArgumentParser(prog="ferry", description="拾页 / Ferry — 网站采集、本地归档、离线筛选。Python 标准库即可运行。")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command")
    crawl = sub.add_parser("crawl", help="开始采集一个网站")
    crawl.add_argument("url", help="HTTP(S) 起始网址")
    crawl.add_argument("-o", "--output", type=Path, required=True, help="新档案目录（必须不存在）")
    crawl.add_argument("-n", "--max-pages", type=positive, default=30, help="本次最多请求页面数，默认 30；重定向跟随请求另计")
    crawl.add_argument("--depth", type=nonnegative, default=2, help="链接深度，起始页为 0，默认 2")
    crawl.add_argument("--include", default="", help="只跟随匹配此正则的网址；起始页豁免")
    crawl.add_argument("--exclude", default="", help="不访问匹配此正则的网址，包括重定向")
    crawl.add_argument("--contains", default="", help="只保留标题/正文包含全部关键词的页面；仍提取其他页面的链接")
    crawl.add_argument("--delay", type=duration, default=0.5, help="请求间隔秒数，默认 0.5；遵守更大的 Crawl-delay")
    crawl.add_argument("--timeout", type=duration, default=10, help="单次网络阻塞超时秒数，默认 10，必须大于 0")
    crawl.add_argument("--max-bytes", type=positive, default=2 * 1024 * 1024, help="单页解压后字节上限，默认 2 MiB")
    crawl.add_argument("--max-queue", type=positive, default=5000, help="累计发现的站内页面上限，默认 5000")
    crawl.add_argument("--json", action="store_true", help="只输出 JSON 汇总")
    resume = sub.add_parser("resume", help="从保存的队列继续采集")
    resume.add_argument("archive", type=Path)
    resume.add_argument("-n", "--max-pages", type=positive, default=30)
    resume.add_argument("--retry-errors", action="store_true", help="重新排队失败请求")
    resume.add_argument("--json", action="store_true")
    for command, help_text in (("stats", "查看归档统计与采集设置"), ("verify", "离线检查保存内容是否缺失或损坏")):
        cmd = sub.add_parser(command, help=help_text)
        cmd.add_argument("archive", type=Path)
        cmd.add_argument("--json", action="store_true")
    search = sub.add_parser("search", help="筛选归档中的页面，无需联网")
    search.add_argument("archive", type=Path)
    filters(search, limit=True)
    search.add_argument("--json", action="store_true")
    export = sub.add_parser("export", help="将筛选结果导出为 Markdown / JSON / CSV")
    export.add_argument("archive", type=Path)
    filters(export)
    export.add_argument("--format", choices=("md", "json", "csv"), default="md")
    export.add_argument("-o", "--output", type=Path, help="输出到新文件；省略时输出到终端")
    read = sub.add_parser("read", help="在终端阅读页面正文或输出原始响应内容")
    read.add_argument("archive", type=Path)
    read.add_argument("id", type=positive, help="search 结果中的编号")
    read.add_argument("--raw", action="store_true", help="输出原始页面；可重定向为 HTML 文件")
    ui = sub.add_parser("browse", help="交互式终端资料馆：筛选、上下选择、离线阅读")
    ui.add_argument("archive", type=Path)
    demo = sub.add_parser("demo", help="实际采集内置测试网站，生成可体验的本地档案")
    demo.add_argument("--interactive", action="store_true", help="演示结束后进入终端资料馆")
    return p


def config_from(args):
    seed = normalize_url(args.url)
    if not seed:
        raise ValueError("请输入不带用户名密码的有效 HTTP(S) 网址")
    if args.timeout <= 0:
        raise ValueError("timeout 必须大于 0")
    for pattern in (args.include, args.exclude):
        if pattern:
            re.compile(pattern)
    return {"seed": seed, "depth": args.depth, "include": args.include,
            "exclude": args.exclude, "contains": args.contains, "delay": args.delay,
            "timeout": args.timeout, "max_bytes": args.max_bytes, "max_queue": args.max_queue}


def progress(url, state, reason):
    labels = {"saved": "+", "filtered": "·", "error": "!", "blocked": "×", "skipped": "-"}
    print(f"  {labels.get(state, '?')} {safe(url)}" + (f"  [{safe(reason)}]" if reason else ""), file=sys.stderr, flush=True)


def selected(archive, args):
    return select_pages(archive.iter_rows(), query=args.query, url=args.url, title=args.title,
                        state=args.state, min_chars=args.min_chars, limit=args.limit)


def csv_cell(value):
    text = "" if value is None else str(value)
    # Spreadsheet applications must not execute scraped text as formulas.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def serialize(rows, format):
    if format == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    if format == "csv":
        stream = io.StringIO(newline="")
        keys = ("id", "url", "final_url", "title", "text", "state", "status", "depth", "fetched_at", "sha256", "reason")
        writer = csv.writer(stream)
        writer.writerow(keys)
        writer.writerows([csv_cell(row[k]) for k in keys] for row in rows)
        return stream.getvalue()
    lines = ["# 拾页 · 离线选集", "", f"共 {len(rows)} 页。正文为采集时的静态文本，保留来源与采集时间。", ""]
    for row in rows:
        title = row["title"].replace("\n", " ") or row["url"]
        lines += ["---", "", "## " + title, "", f"来源：<{row['url']}>",
                  f"采集：{row['fetched_at'] or '未请求'} · 状态：{row['state']}", ""]
        # Render scraped prose as a quote rather than active Markdown HTML.
        lines += ["> " + line.replace("<", "&lt;").replace(">", "&gt;") for line in (row["text"] or row["reason"]).splitlines()]
        lines += [""]
    return "\n".join(lines)


def run_demo(interactive=False):
    from .demo import demo_site
    demos = Path.cwd() / ".local" / "demos"
    demos.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="demo-", dir=demos))
    output = root / "archive"
    print(banner(), flush=True)
    print("\n  演示：采集本地 HTTP 网站 → 暂停 → 续爬 → 筛选 → 导出 → 校验\n", flush=True)
    with demo_site() as (url, hits):
        config = {"seed": url, "depth": 2, "include": "", "exclude": "", "contains": "",
                  "delay": 0, "timeout": 3, "max_bytes": 2 * 1024 * 1024, "max_queue": 100}
        with Archive(output, config=config) as archive:
            Crawler(archive, progress).run(3)
            print("\n  已采集 3 页，模拟暂停。重新打开数据库继续……\n", flush=True)
        with Archive(output) as archive:
            stats = Crawler(archive, progress).run(30)
            print(summary(stats))
            matches = select_pages(archive.rows(), query="离线")
            print(results(matches, "离线"))
            (root / "离线选集.md").write_text(serialize(matches, "md"), encoding="utf-8")
            issues = archive.verify()
            if issues:
                raise ValueError(f"演示档案校验失败：{issues}")
            print(f"  SHA-256 校验通过。{stats['counts']['saved']} 个网址共用 {stats['objects']} 个内容对象。")
            print("  robots 禁区与外站均未访问；404 和二进制附件已记录原因。")
            print(f"\n  留下的资料可继续体验：\n\n    python3 -m ferry browse {output.relative_to(Path.cwd())}")
            print(f"    python3 -m ferry search {output.relative_to(Path.cwd())} 离线\n")
            print(f"  Markdown 选集：{root.relative_to(Path.cwd()) / '离线选集.md'}\n")
            if interactive:
                if not sys.stdin.isatty() or not sys.stdout.isatty():
                    raise ValueError("交互模式需要真实终端；可以直接运行 demo 查看文字演示")
                browse(archive)
    return 0


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    try:
        if args.command is None:
            print(banner())
            p.print_help()
            return 0
        if args.command == "demo":
            return run_demo(args.interactive)
        if args.command == "crawl":
            config = config_from(args)
            with Archive(args.output, config=config) as archive:
                stats = Crawler(archive, None if args.json else progress).run(args.max_pages)
            print(json.dumps(stats, ensure_ascii=False, indent=2) if args.json else summary(stats))
            return 1 if stats["counts"]["error"] else 0
        with Archive(args.archive) as archive:
            if args.command == "resume":
                stats = Crawler(archive, None if args.json else progress).run(args.max_pages, retry_errors=args.retry_errors)
                print(json.dumps(stats, ensure_ascii=False, indent=2) if args.json else summary(stats))
                return 1 if stats["counts"]["error"] else 0
            if args.command == "stats":
                stats = archive.stats()
                print(json.dumps(stats, ensure_ascii=False, indent=2) if args.json else summary(stats))
            elif args.command == "search":
                rows = selected(archive, args)
                print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else results(rows, args.query))
            elif args.command == "export":
                content = serialize(selected(archive, args), args.format)
                if args.output:
                    with args.output.open("x", encoding="utf-8", newline="") as stream:
                        stream.write(content)
                    print(f"已导出：{args.output}", file=sys.stderr)
                else:
                    print(content if not sys.stdout.isatty() else safe(content), end="")
            elif args.command == "verify":
                issues = archive.verify()
                if args.json:
                    print(json.dumps({"ok": not issues, "issues": issues}, ensure_ascii=False, indent=2))
                elif issues:
                    for issue in issues:
                        print(safe(f"! {issue['sha256'] or '数据库'}  {issue['reason']}"))
                else:
                    print(f"校验通过 · {archive.stats()['objects']} 个内容对象 · SQLite integrity_check 正常")
                return 1 if issues else 0
            elif args.command == "read":
                row = archive.db.execute("SELECT * FROM pages WHERE id=?", (args.id,)).fetchone()
                if not row:
                    raise ValueError(f"不存在编号 {args.id}")
                if args.raw:
                    if not row["sha256"]:
                        raise ValueError("该页面没有保存原始内容")
                    body = archive.object_path(row["sha256"]).read_bytes()
                    if sys.stdout.isatty():
                        print(safe(body.decode("utf-8", errors="replace")))
                    else:
                        sys.stdout.buffer.write(body)
                else:
                    print(safe(f"\n{row['title']}\n{row['url']}\n{row['fetched_at'] or ''}\n\n{row['text'] or row['reason']}\n"))
            elif args.command == "browse":
                if not sys.stdin.isatty() or not sys.stdout.isatty():
                    raise ValueError("browse 需要真实终端；非交互环境请使用 search 或 read")
                browse(archive)
        return 0
    except KeyboardInterrupt:
        print("\n已暂停。已完成页面与队列均已保存，使用 resume 继续。", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0
    except (ValueError, OSError, sqlite3.Error, re.error, ImportError) as exc:
        print(f"拾页：{safe(exc)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
