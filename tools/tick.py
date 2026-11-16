"""KEYWORDS.md の表で、番号の行の「動画」を ○ にする（動画・ショート・サムネができて目で確かめたら）。 python tools/tick.py 0039 [0040 ...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kw
for num in sys.argv[1:]:
    kw.update(num, 動画="○")
    print("ok", num)
