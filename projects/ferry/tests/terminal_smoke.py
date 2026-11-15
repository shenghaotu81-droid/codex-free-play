"""Exercise the real curses app in a CPU-only pseudo-terminal. No browser/GPU."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ferry.archive import Archive


def run():
    local = ROOT / ".local" / "tests"
    local.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="terminal-", dir=local) as temporary:
        root = Path(temporary) / "archive"
        config = {"seed": "https://demo.invalid/"}
        with Archive(root, config=config) as archive:
            for index, (title, text) in enumerate([
                ("第一份资料", "保存页面与出处。"),
                ("SQLite 离线指南", "SQLite 正文可以完全离线阅读。\n" * 60),
                ("阳台种菜", "番茄和薄荷的浇水记录。"),
            ]):
                url = config["seed"] + str(index)
                if index == 0:
                    archive.db.execute("UPDATE pages SET url=? WHERE id=1", (url,))
                    page_id = 1
                else:
                    page_id = archive.db.execute("INSERT INTO pages(url,depth) VALUES (?,1)", (url,)).lastrowid
                digest = archive.save_object(text.encode())
                archive.finish(page_id, state="saved", title=title, text=text, bytes=len(text.encode()), sha256=digest, status=200)
            archive.db.commit()
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 90, 0, 0))
        env = dict(os.environ, TERM="xterm-256color", PYTHONDONTWRITEBYTECODE="1")
        process = subprocess.Popen([sys.executable, "-m", "ferry", "browse", str(root)], cwd=ROOT,
                                   stdin=slave, stdout=slave, stderr=slave, env=env, start_new_session=True)
        os.close(slave)

        def collect(expected=None, timeout=4):
            captured = bytearray()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    captured.extend(chunk)
                    if expected is not None and expected.encode() in captured:
                        return bytes(captured)
                elif expected is None:
                    break
            if expected is not None and expected.encode() not in captured:
                raise AssertionError(f"Terminal did not display {expected!r}: {captured.decode(errors='replace')}")
            return bytes(captured)

        try:
            collect("FERRY")
            os.write(master, b"j\n")
            collect("SQLite 正文")
            collect()
            os.write(master, b" ")
            assert collect(), "scroll did not redraw the terminal"
            os.write(master, b"q")
            collect()
            os.write(master, b"/SQLite\n")
            collect("SQLite")
            # Resize the real terminal and ensure the app remains responsive.
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 16, 50, 0, 0))
            os.kill(process.pid, signal.SIGWINCH)
            collect()
            os.write(master, b"a")
            collect()
            os.write(master, b"q")
            code = process.wait(timeout=4)
            assert code == 0, f"browse exited {code}"
            print("PASS: terminal launch, select, read, scroll, search, resize, toggle and quit (CPU only)")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            os.close(master)


if __name__ == "__main__":
    run()
