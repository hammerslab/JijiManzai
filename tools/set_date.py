"""KEYWORDS.md の表で、番号の行の「YouTube」を「予約 YYYY/MM/DD」にする（時刻は 19:00 固定）。 python tools/set_date.py 0006 2026/11/09 [公開済み]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kw
n, d = sys.argv[1], sys.argv[2]
state = sys.argv[3] if len(sys.argv) > 3 else "予約"
kw.update(n, YouTube=f"{state} {d}")
print("ok", n, state, d)
