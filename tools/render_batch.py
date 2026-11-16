"""台本の名前を並べて、動画・ショート・サムネイルを何本かずつ同時に作る。

    python tools/render_batch.py 0085_selfregi 0086_kenshin ... [-j 3]

1 本ごとのログは build/work/render_<名前>.log。終わった順に「ok 名前 秒」か「NG 名前」を出す。
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def one(name):
    log = ROOT / "build" / "work" / f"render_{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8") as f:
        for tool in ("render.py", "short.py", "thumbnail.py"):
            r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "proto" / tool), name], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
            if r.returncode:
                return name, f"NG（{tool}）"
    mp4 = ROOT / "build" / "anim" / f"{name}.mp4"
    return name, "ok" if mp4.exists() else "NG（mp4 がない）"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("-j", type=int, default=3)
    args = ap.parse_args()
    with ThreadPoolExecutor(args.j) as ex:
        for fut in as_completed([ex.submit(one, n) for n in args.names]):
            name, res = fut.result()
            print(res, name, flush=True)


if __name__ == "__main__":
    main()
