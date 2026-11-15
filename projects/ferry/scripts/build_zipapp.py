"""Build one runnable artifact without pip, downloads, or writing outside the repo."""
from pathlib import Path
import shutil
import tempfile
import zipapp

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / ".local" / "dist"
DEST.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix=".build-", dir=DEST) as temporary:
    source = Path(temporary)
    shutil.copytree(ROOT / "ferry", source / "ferry", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (source / "__main__.py").write_text("from ferry.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
    zipapp.create_archive(source, DEST / "ferry.pyz", interpreter="/usr/bin/env python3", compressed=True)
print(DEST / "ferry.pyz")
