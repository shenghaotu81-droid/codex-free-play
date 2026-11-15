"""Human-readable terminal views. All untrusted page text is control-escaped."""
from __future__ import annotations

import re
import shutil
import unicodedata

LABELS = {"saved": "已保存", "pending": "待采集", "filtered": "未保留", "blocked": "已拦截",
          "skipped": "已跳过", "error": "请求失败"}


def safe(value) -> str:
    result = []
    for char in str(value):
        category = unicodedata.category(char)
        if char == "\n":
            result.append(char)
        elif char == "\t":
            result.append("  ")
        elif category.startswith("C"):
            result.append(f"\\u{ord(char):04x}")
        else:
            result.append(char)
    return "".join(result)


def cell_width(value: str) -> int:
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in value)


def clip(value, width: int) -> str:
    value = safe(value).replace("\n", " ")
    if cell_width(value) <= width:
        return value
    result, used = [], 0
    for c in value:
        n = cell_width(c)
        if used + n > max(0, width - 1):
            break
        result.append(c)
        used += n
    return "".join(result) + ("…" if width > 0 else "")


def wrap(value: str, width: int) -> list[str]:
    lines = []
    for original in safe(value).splitlines():
        current, used = "", 0
        for c in original:
            n = cell_width(c)
            if used + n > width and current:
                lines.append(current)
                current, used = "", 0
            current += c
            used += n
        lines.append(current)
    return lines


def size(value: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{value} B"
        value /= 1024


def banner(width=88) -> str:
    return "\n".join(["", "  拾 页  /  F E R R Y", "  把散落的网页，渡到自己的资料库。", "  " + "─" * max(10, width - 4)])


def summary(stats: dict) -> str:
    width = min(96, shutil.get_terminal_size((88, 24)).columns)
    counts = stats["counts"]
    total = sum(counts.values())
    finished = total - counts["pending"]
    bar_size = min(32, max(10, width - 32))
    fill = round(bar_size * finished / total) if total else 0
    lines = [banner(width), "", "  起点  " + clip(stats["seed"], width - 10),
             f"  进度  {'━' * fill}{'─' * (bar_size - fill)}  {finished}/{total}", ""]
    for keys in (("saved", "pending", "filtered"), ("blocked", "skipped", "error")):
        lines.append("  " + "    ".join(f"{LABELS[k]} {counts[k]:>4}" for k in keys))
    lines += ["", f"  存储  {stats['objects']} 个内容对象 · {size(stats['stored_bytes'])}",
              f"  去重  节约 {size(stats['deduplicated_bytes'])} · 已发现 {sum(stats['links'].values())} 条链接",
              "  档案  " + safe(stats["archive"])]
    if counts["pending"]:
        lines += ["", "  队列已保存。使用 resume 继续采集。"]
    if counts["error"]:
        lines += ["  有失败请求。search --state error 可查看原因；resume --retry-errors 可重试。"]
    return "\n".join(lines) + "\n"


def snippet(text: str, query: str, width: int) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    hits = [flat.casefold().find(t.casefold()) for t in query.split()]
    hits = [h for h in hits if h >= 0]
    start = max(0, min(hits) - 24) if hits else 0
    return ("…" if start else "") + clip(flat[start:], width - (1 if start else 0))


def results(rows: list[dict], query: str = "") -> str:
    width = max(40, min(110, shutil.get_terminal_size((88, 24)).columns))
    lines = [f"\n  找到 {len(rows)} 条记录" + (f" · {safe(query)}" if query else ""), ""]
    for row in rows:
        lines += [f"  {row['id']:>4}  {LABELS[row['state']]}  {clip(row['title'] or '(无标题)', width - 22)}",
                  "        " + clip(row["url"], width - 10),
                  "        " + snippet(row["text"] or row["reason"], query, width - 10), ""]
    if not rows:
        lines.append("  试试减少关键词，或用 --state all 查看未保存的记录。\n")
    return "\n".join(lines)


def screen_lines(stats: dict, rows: list[dict], selected: int, query: str, width: int, height: int) -> list[str]:
    """Pure renderer, also exercised by CPU-only tests at narrow terminal sizes."""
    if width < 44 or height < 14:
        return [clip("拾页 / Ferry", width), clip("请把终端放大至 44 列 × 14 行；q 退出", width)]
    counts = stats["counts"]
    lines = ["  拾页 / FERRY                                      本地档案馆",
             "  " + stats["seed"],
             f"  已保存 {counts['saved']}    待采集 {counts['pending']}    失败 {counts['error']}    对象 {stats['objects']}",
             "  " + "─" * (width - 4), f"  筛选 / {query or '全部标题与正文'}   · {len(rows)} 条", ""]
    capacity = max(1, (height - 12) // 2)
    start = (selected // capacity) * capacity
    for index in range(start, min(len(rows), start + capacity)):
        row = rows[index]
        prefix = " ›" if index == selected else "  "
        lines += [f"{prefix} {row['id']:>3}  {LABELS[row['state']]}  {row['title'] or '(无标题)'}",
                  "           " + row["url"]]
    while len(lines) < height - 6:
        lines.append("")
    lines.append("  " + "─" * (width - 4))
    if rows:
        row = rows[min(selected, len(rows) - 1)]
        lines += ["  " + snippet(row["text"] or row["reason"], query, width - 5),
                  f"  深度 {row['depth']} · {size(row['bytes'])} · HTTP {row['status'] or '—'} · {row['fetched_at'] or '尚未请求'}"]
    else:
        lines += ["  没有匹配记录。按 / 修改关键词，按 a 切换全部状态。", ""]
    lines += ["", "  ↑↓ / j k 选择   Enter 阅读   / 搜索   a 全部/已保存   q 退出"]
    return [clip(line, width - 1) for line in lines[:height]]


def browse(archive):
    import curses
    from .archive import select_pages

    def session(stdscr):
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        all_rows = archive.rows()
        stats = archive.stats()
        query, state, selected, offset, reading = "", "saved", 0, 0, False
        while True:
            height, width = stdscr.getmaxyx()
            rows = select_pages(all_rows, query=query, state=state)
            selected = max(0, min(selected, len(rows) - 1))
            stdscr.erase()
            if reading and rows:
                row = rows[selected]
                body = wrap(row["text"] or row["reason"], max(8, width - 4))
                offset = min(offset, max(0, len(body) - max(1, height - 7)))
                lines = ["  " + clip(row["title"] or "(无标题)", width - 4), "  " + clip(row["url"], width - 4),
                         "  " + "─" * max(0, width - 4)]
                lines += ["  " + line for line in body[offset:offset + max(1, height - 7)]]
                lines += ["", f"  行 {offset + 1}/{max(1, len(body))}   ↑↓ 滚动 · 空格 翻页 · q 返回"]
            else:
                lines = screen_lines(stats, rows, selected, query + ("  [全部状态]" if state == "all" else ""), width, height)
            for y, line in enumerate(lines[:height]):
                try:
                    attr = curses.A_BOLD if y == 0 else curses.A_REVERSE if line.startswith(" ›") else 0
                    stdscr.addstr(y, 0, clip(line, max(0, width - 1)), attr)
                except curses.error:
                    pass
            stdscr.refresh()
            key = stdscr.get_wch()
            if key in ("q", "\x1b"):
                if reading:
                    reading = False
                else:
                    break
            elif key in (curses.KEY_DOWN, "j"):
                if reading:
                    offset += 1
                else:
                    selected += 1
            elif key in (curses.KEY_UP, "k"):
                if reading:
                    offset = max(0, offset - 1)
                else:
                    selected = max(0, selected - 1)
            elif key in (" ", curses.KEY_NPAGE) and reading:
                offset += max(1, height - 8)
            elif key == curses.KEY_PPAGE and reading:
                offset = max(0, offset - max(1, height - 8))
            elif key in ("\n", "\r", curses.KEY_ENTER) and rows:
                reading, offset = True, 0
            elif key == "a" and not reading:
                state, selected = ("all" if state == "saved" else "saved"), 0
            elif key == "/" and not reading:
                value = ""
                while True:
                    stdscr.move(height - 1, 0)
                    stdscr.clrtoeol()
                    try:
                        stdscr.addstr(height - 1, 0, clip("  搜索：" + value + "▏", width - 1))
                    except curses.error:
                        pass
                    stdscr.refresh()
                    char = stdscr.get_wch()
                    if char in ("\n", "\r", curses.KEY_ENTER):
                        query, selected = value, 0
                        break
                    if char == "\x1b":
                        break
                    if char in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                        value = value[:-1]
                    elif isinstance(char, str) and char.isprintable():
                        value += char
    try:
        curses.wrapper(session)
    except curses.error as exc:
        raise ValueError(f"无法初始化终端界面：{exc}；可改用 search 和 read") from exc
