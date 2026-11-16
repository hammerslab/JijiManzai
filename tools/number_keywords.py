"""台本ができたキーワードに番号を付け（KEYWORDS.md）、scripts/README.md の表に行を足す。

    python tools/number_keywords.py build/work/gists.json

gists.json：{"0039_tawaman": {"key": "タワマン", "gist": "ネタの概要"}, ...}
- KEYWORDS.md は直す直前に読み、「まだ台本がないキーワード」の「- <key>」で始まる行を消して、表の番号順の位置に行を足す。ほかの行は触らない
- README の表は、まだその番号の行がなければ、番号順の位置に足す
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
gists = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

# KEYWORDS.md：「まだ台本がないキーワード」の箇条書きから、表の行に移す
sys.path.insert(0, str(ROOT / "tools"))
import kw
L, rows = kw.load()
for name, g in sorted(gists.items()):
    num = name[:4]
    if num in rows:
        continue
    hits = [i for i, l in enumerate(L) if l.startswith("- " + g["key"])]
    if len(hits) != 1:
        print("KEYWORDS で見つからない／複数:", name, g["key"], hits)
        continue
    s = (ROOT / "scripts" / f"{name}.txt").read_text(encoding="utf-8")
    title = re.search(r"^title:\s*(.+)$", s, re.M).group(1).strip()
    combo = "男性" if re.search(r"^combo:\s*male", s, re.M) else "女性"
    del L[hits[0]]
    r = dict(zip(kw.COLS, [num, g.get("label", g["key"]), title, combo, "○", "未", "未", "未", g["gist"].replace("|", "／")]))
    # 表の番号順の位置に入れる
    at = {l[2:6]: i for i, l in enumerate(L) if re.match(r"^\| \d{4} \|", l)}
    pos = max([i for n2, i in at.items() if n2 < num], default=max(at.values())) + 1
    L.insert(pos, kw.fmt(r))
    rows[num] = None
kw.save(L)

# README の表
p = ROOT / "scripts" / "README.md"
R = p.read_text(encoding="utf-8").splitlines()
rows = [i for i, l in enumerate(R) if re.match(r"\| \d{4} \|", l)]
for name in sorted(gists):
    num = name[:4]
    if any(R[i].startswith(f"| {num} |") for i in rows):
        continue
    s = (ROOT / "scripts" / f"{name}.txt").read_text(encoding="utf-8")
    title = re.search(r"^title:\s*(.+)$", s, re.M).group(1).strip()
    theme = re.search(r"^theme:\s*(.+)$", s, re.M).group(1).strip()
    combo = "男性" if re.search(r"^combo:\s*male", s, re.M) else "女性"
    d = json.loads((ROOT / "build" / name / "timeline_voicevox.json").read_text(encoding="utf-8"))["duration"]
    row = f"| {num} | [{name}]({name}.md) | {title} | {theme} | {combo} | {int(d // 60)}分{int(round(d % 60)):02d}秒 | あり |"
    # 番号順の位置に入れる
    pos = max([i for i in rows if R[i][2:6] < num], default=rows[-1]) + 1
    R.insert(pos, row)
    rows = [i for i, l in enumerate(R) if re.match(r"\| \d{4} \|", l)]
p.write_text("\n".join(R) + "\n", encoding="utf-8", newline="\n")
print("ok")
