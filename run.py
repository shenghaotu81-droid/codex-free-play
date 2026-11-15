"""Run either project from the repository root, keeping output in its project."""
import os
from pathlib import Path
import runpy
import sys

PROJECTS = {"ferry": ("ferry", "ferry"), "exchange": ("exchange-sim", "exchange_sim")}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in PROJECTS:
        print("Usage: python3 run.py {ferry|exchange} [project arguments]")
        return 0 if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help") else 2
    directory, module = PROJECTS[sys.argv[1]]
    project = Path(__file__).resolve().parent / "projects" / directory
    os.chdir(project)
    sys.path.insert(0, str(project))
    sys.argv = [module, *sys.argv[2:]]
    runpy.run_module(module, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
