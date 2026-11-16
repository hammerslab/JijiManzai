"""KEYWORDS.md の進捗表を読み書きする（tick.py・set_date.py・set_short.py・mk_short.py・number_keywords.py が使う）。

表の列：| # | キーワード | 題名 | コンビ | 台本 | 動画 | YouTube | ショート | ネタの概要 |
- YouTube：「未」／「予約 2026/11/09」／「公開済み 2026/10/20」（時刻はいつも 19:00）
- ショート：「未」／「公開済み 2026/10/26（関連動画あり）」など
直す直前に読み、表の行だけを書き換える（ほかの行は触らない）。
"""
import re
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "KEYWORDS.md"
COLS = ["#", "キーワード", "題名", "コンビ", "台本", "動画", "YouTube", "ショート", "ネタの概要"]


def load():
    L = P.read_text(encoding="utf-8").splitlines()
    rows = {}
    for i, l in enumerate(L):
        if re.match(r"^\| \d{4} \|", l):
            cells = [c.strip() for c in l.strip().strip("|").split(" | ")]
            rows[cells[0]] = (i, dict(zip(COLS, cells)))
    return L, rows


def fmt(r):
    return "| " + " | ".join(r[c] for c in COLS) + " |"


def save(L, n0=None):
    if n0 is not None:
        assert len(L) == n0, (len(L), n0)
    P.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def update(num, **kw):
    """番号の行の列を書き換える。例：update("0039", 動画="○")"""
    L, rows = load()
    n0 = len(L)
    i, r = rows[num]
    r.update(kw)
    L[i] = fmt(r)
    save(L, n0)
    return r
