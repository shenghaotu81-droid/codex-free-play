"""Extract a committed snapshot read-only; all generated files stay in this project."""
import argparse
import json
from pathlib import Path
import subprocess

PROJECT = Path(__file__).resolve().parents[1]
PIN = "e25d4c98995fff395cf342f20b5fa1ef207a8afb"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.home()/"projects/campus-marker-opencv-assignment")
    parser.add_argument("--revision", default=PIN, help="committed revision; working-tree changes are never used")
    args = parser.parse_args()
    def git(*parts):
        return subprocess.check_output(["git", "-C", str(args.source), *parts])
    revision = git("rev-parse", args.revision+"^{commit}").decode().strip()
    local = PROJECT/".local"
    snapshot = local/"sources"/revision
    prefix = "src/tushenghao/"
    allowed = [prefix+s for s in ("include/", "config/", "src/types/", "src/config/", "src/detection/", "src/pose/", "src/tracking/")]
    paths = git("ls-tree", "-rz", "--name-only", revision).decode().split("\0")
    count = 0
    for name in paths:
        if not any(name.startswith(p) for p in allowed):
            continue
        target = snapshot/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git("show", revision+":"+name))
        count += 1
    build = local/"build"/revision
    subprocess.run(["cmake", "-S", str(PROJECT/"native"), "-B", str(build),
                    "-DCMAKE_BUILD_TYPE=Release", "-DCAMPUS_SOURCE="+str(snapshot)], check=True)
    subprocess.run(["cmake", "--build", str(build), "-j", "2"], check=True)
    manifest = {"revision":revision, "source":str(args.source.resolve()), "extracted_files":count,
                "binary":str(build/"campus_bridge"), "config":str(snapshot/prefix/"config")}
    (local/"campus-bridge.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
