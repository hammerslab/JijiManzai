"""VOICEVOX が台本をどう読むかを、カナで書き出す（読み間違い探し用。音は作らない）。

    python proto/vv_kana.py chappy influencer hacker ending_male ending_female   # proto/ の台本
    python proto/vv_kana.py scripts/dopagaki.txt                                # 場所を指定して

できるもの：build/kana/<台本>.txt（行ごとに「読ませる文」と「VOICEVOX の読み（カナ）」）
VOICEVOX は、読む前に読みをカナで返す（audio_query の kana）。'＝アクセントの位置、/＝句の切れ目、、＝間。
"""
import json
import sys
import urllib.parse
from pathlib import Path

import synth
from synth import ROOT

HERE = Path(__file__).parent


def main():
    cfg = json.loads((HERE / "voices.json").read_text(encoding="utf-8-sig"))
    out_dir = ROOT / "build" / "kana"
    out_dir.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[1:]:
        src = Path(arg) if arg.endswith(".txt") else HERE / f"{arg}.txt"
        name = src.stem
        combo, lines, _ = synth.parse(src)
        rows = []
        for who, _, segs, shown, _ in lines:
            if who == "LOOK":
                continue
            for text, style, _ in segs:
                s = synth.vv_settings(cfg, combo, "A" if who == "AB" else who, style)
                spoken = synth.reading(text, cfg, "voicevox").replace("[pause short]", "、").replace("[pause long]", "、、、").replace("[pause]", "、、")
                sid = synth.vv_style_id(s["character"], s["style"])
                q = json.loads(synth.vv_request(f"/audio_query?text={urllib.parse.quote(spoken)}&speaker={sid}"))
                rows.append(f"{who}\t{spoken}\n\t{q['kana']}")
        (out_dir / f"{name}.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
        print(out_dir / f"{name}.txt", len(rows), "行")


if __name__ == "__main__":
    main()
