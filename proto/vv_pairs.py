"""VOICEVOX のコンビの組み合わせを、本番の台本の掛け合いで聴き比べる。台本の頭から数十秒を、組み合わせごとに読ませてつなぐ。

    python proto/vv_pairs.py

できるもの：build/compare/vv_pairs_<male|female>.mp3 と、何番がどの組み合わせかの .txt
VOICEVOX のアプリを起動しておく。
"""
import array
import copy
import json
import subprocess
import sys
import wave
from pathlib import Path

import synth
from synth import RATE, ROOT
from vv_compare import ANNOUNCER, NUMS

HERE = Path(__file__).parent
# コンビ：(台本, 使う行数, [(ボケ, ツッコミ, ツッコミの調整), ...])。キャラは (名前, スタイル)。調整は voices.json の値を上書き
PAIRS = {
    "female": ("influencer.txt", 13, [
        (("波音リツ", None), ("あんこもん", "つよつよ"), {"intonation": 1.2, "pitch": 0.0}),
        (("波音リツ", None), ("あんこもん", "つよつよ"), {"intonation": 1.4, "pitch": -0.03}),
        (("波音リツ", None), ("あんこもん", "つよつよ"), {"intonation": 1.7, "pitch": -0.06}),
    ]),
    "male": ("chappy.txt", 11, [
        (("麒ヶ島宗麟", None), ("白上虎太郎", "ふつう"), {"intonation": 1.2, "pitch": 0.0}),
        (("麒ヶ島宗麟", None), ("白上虎太郎", "ふつう"), {"intonation": 1.4, "pitch": -0.03}),
        (("麒ヶ島宗麟", None), ("白上虎太郎", "ふつう"), {"intonation": 1.7, "pitch": -0.06}),
    ]),
}


def excerpt(script, n_lines, out):
    """台本の頭の設定と、セリフを n_lines 行だけ。"""
    head, body = [], []
    for line in (HERE / script).read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        (head if t.split(":")[0] in ("combo", "title", "theme", "thumb", "short") else body).append(t)
    out.write_text("\n".join(head + body[:n_lines]) + "\n", encoding="utf-8")


def main():
    base = json.loads((HERE / "voices.json").read_text(encoding="utf-8-sig"))
    out_dir = ROOT / "build" / "compare"
    work = out_dir / "vv_pairs"
    work.mkdir(parents=True, exist_ok=True)
    for combo in sys.argv[1:] or PAIRS:
        script, n_lines, pairs = PAIRS[combo]
        src = work / f"{combo}_excerpt.txt"
        excerpt(script, n_lines, src)
        pcm, listing = array.array("h"), []
        for i, (boke, tsk, tune) in enumerate(pairs, 1):
            cfg = copy.deepcopy(base)
            for role, (ch, st) in (("A", boke), ("B", tsk)):
                cfg["voicevox"]["combos"][combo][role].update({"character": ch, "style": st})
            cfg["voicevox"]["combos"][combo]["B"].update(tune)
            vfile = work / f"{combo}_{i}.json"
            vfile.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
            name = f"vv_pair_{combo}_{i}"
            subprocess.run([sys.executable, str(HERE / "synth.py"), str(src), "--backend", "voicevox",
                            "--voices", str(vfile), "--name", name], check=True, stdout=subprocess.DEVNULL)
            lab = work / f"label_{i}.wav"
            synth.process(synth.synth_raw(f"{NUMS[i - 1]}ばん", ANNOUNCER, "chirp"), lab, ANNOUNCER, "chirp")
            pcm += synth.read_pcm(lab) + array.array("h", bytes(2 * int(0.4 * RATE)))
            pcm += synth.read_pcm(ROOT / "build" / name / f"{name}_voicevox.wav") + array.array("h", bytes(2 * RATE))
            listing.append(f"{i} 番  ボケ：{boke[0]}（{boke[1] or '最初のスタイル'}）／ツッコミ：{tsk[0]}（{tsk[1] or '最初のスタイル'}）"
                           f"　ツッコミの抑揚 {tune['intonation']}・ピッチ {tune['pitch']:+}")
        wav = out_dir / f"vv_pairs_{combo}.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        subprocess.run([synth.ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "192k", str(wav.with_suffix(".mp3"))], check=True)
        wav.unlink()
        (out_dir / f"vv_pairs_{combo}.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
        print(f"vv_pairs_{combo}: {len(pcm) / RATE:.1f} 秒")
        print("\n".join(listing))


if __name__ == "__main__":
    main()
