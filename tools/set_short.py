"""KEYWORDS.md の表で、番号の行の「ショート」を書く。 python tools/set_short.py 0004 2026/10/26 あり|なし [予約]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kw
n, d, rel = sys.argv[1], sys.argv[2], sys.argv[3]
state = sys.argv[4] if len(sys.argv) > 4 else "公開済み"
kw.update(n, ショート=f"{state} {d}（関連動画{rel}）")
print("ok", n, state, d, rel)
