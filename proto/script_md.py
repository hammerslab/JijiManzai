"""台本（.txt）から、人が読みやすい版（.md）を作る。記号を、役名・間・叩く・声の変わり目の言葉に直す。

    python proto/script_md.py scripts/dopagaki.txt scripts/maratan.txt

できるもの：台本と同じ場所に <台本>.md。声を作ってあれば（build/<台本>/timeline_*.json）、長さも書く。
"""
import json
import re
import sys
from pathlib import Path

import synth
from synth import ROOT

ROLE = {
    "male": {"A": "ボケ・アフロ", "B": "ツッコミ・モヒカン"},
    "female": {"A": "ボケ・ボブ", "B": "ツッコミ・ギャル"},
}
STYLE = {"robot": "機械の声", "system": "アナウンスの声", "shibui": "かっこつけた声", "jii": "おじいさんの声",
         "cute": "作った高い声", "polite": "丁寧な棒読み", "chappy": "AIっぽい口調", "whisper": "小声"}
QUOTE_RE = re.compile(r"「([^」]*)」@(\w+)")


def to_md(path):
    path = Path(path)
    combo, lines, meta = synth.parse(path)
    roles = ROLE[combo]
    cfg = json.loads((Path(__file__).parent / "voices.json").read_text(encoding="utf-8-sig"))
    prefix = cfg["combos"][combo]["tsukkomi"]["prefix"]   # 叩くツッコミの頭に自動で付く言葉
    out = [f"# {meta.get('title', path.stem)}", "",
           f"- お題：{meta.get('theme', '')}",
           f"- コンビ：{'男性' if combo == 'male' else '女性'}　{roles['A']}／{roles['B']}"]
    for backend in ("voicevox", "chirp"):
        tl = ROOT / "build" / path.stem / f"timeline_{backend}.json"
        if tl.exists():
            d = json.loads(tl.read_text(encoding="utf-8"))["duration"]
            out.append(f"- 長さ：{int(d // 60)}分{int(d % 60):02d}秒（{'VOICEVOX' if backend == 'voicevox' else 'Google'} の声で作ったとき）")
            break
    out += ["", f"記号：〔間〕＝少し黙る、【叩く】【強く叩く】【思いきり叩く】＝手刀でツッコむ（効果音つき。頭の「{prefix}」は自動で付く）、〈〉＝そこだけ声を変える", "", "---", ""]
    raw = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    body = [ln for ln in raw if ln and not ln.startswith("#") and not ln.startswith(("combo:", "title:", "theme:"))]
    for ln in body:
        look = synth.LOOK_RE.match(ln)
        if look:
            out.append(f"> 〔{look.group(1)} 秒、2 人で見つめ合う〕")
            out.append("")
            continue
        m = synth.LINE_RE.match(ln)
        who, hit, gap, text = m.group(1), m.group(2), m.group(3), m.group(4)
        text = synth.RUBY_RE.sub(r"\1", text)
        text = synth.TAG_RE.sub("〔間〕", text)
        text = QUOTE_RE.sub(lambda q: f"「{q.group(1)}」〈{STYLE.get(q.group(2), q.group(2))}〉", text)
        name = "2 人" if who == "AB" else roles[who]
        pre = "〔間〕" if gap and float(gap) >= 0.4 else ""
        mark = f"【{['', '叩く', '強く叩く', '思いきり叩く'][len(hit or '')]}】{prefix} " if hit else ""
        out.append(f"**{name}**　{pre}{mark}{text}")
        out.append("")
    md = path.with_suffix(".md")
    md.write_text("\n".join(out), encoding="utf-8")
    return md


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(to_md(p))
