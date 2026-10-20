"""VOICEVOX の声の聴き比べ。役ごとに、候補のキャラが同じセリフを読む。各候補の前に「n 番」と案内が入る。

    python proto/vv_compare.py                 # すべての役（各キャラの最初のスタイル）
    python proto/vv_compare.py male_boke       # 役を選んで
    python proto/vv_compare.py --all-styles    # 各キャラのスタイルを全部（長くなる）

できるもの：build/compare/vv_<役>.mp3 と、何番が誰のどのスタイルかの vv_<役>.txt
VOICEVOX のアプリを起動しておく（http://127.0.0.1:50021）。
"""
import array
import json
import subprocess
import sys
import wave
from pathlib import Path

import synth
from synth import RATE, ROOT

CFG = json.loads((Path(__file__).parent / "voices.json").read_text(encoding="utf-8-sig"))
# 役：候補（キャラ, [スタイル...]。空ならそのキャラの最初のスタイル）、読ませるセリフ、速さ・抑揚（いまの台本の役に合わせた仮の値）
ROLES = {
    "female_boke": ([("中国うさぎ", []), ("猫使アル", ["ノーマル", "おちつき"]), ("波音リツ", ["ノーマル", "クイーン"])], [
        "私、インフルエンサーになることにした。",
        "3人。",
        "お母さんと、おばあちゃんと、私のサブアカウント。",
        "フォロワーが、1万人増えた。あなたの。",
    ], {"speed": 1.0, "intonation": 0.9}),
    "female_tsukkomi": ([("あんこもん", ["ノーマル", "つよつよ"]), ("No.7", [])], [
        "えぐーー！ 身内しかいないし、しかも1人、自分じゃーーん！",
        "テンション急に上がった！ その声どっから出てんの！ 普段のあんたと別人じゃーん！",
        "町内会、企業じゃないじゃん！",
    ], {"speed": 1.15, "intonation": 1.2}),
    "male_boke": ([("雀松朱司", []), ("青山龍星", ["ノーマル", "しっとり"]), ("麒ヶ島宗麟", []), ("栗田まろん", [])], [
        "そうかな。",
        "結論から言うと、カレーです。ポイントは3つあります。",
        "……田中さんは、関係ないだろ。",
    ], {"speed": 1.0, "intonation": 0.9}),
    "male_tsukkomi": ([("白上虎太郎", ["ふつう", "おこ"]), ("玄野武宏", ["ノーマル", "ツンギレ"])], [
        "ワッーーツ！ 全部カレーの説明だろ！ 3つ目に至っては、ただのカレーだよ！",
        "急に寄り添うな！ 気持ち悪いよ！ 目を見て言え、目を！",
        "評価しねえよ！",
    ], {"speed": 1.15, "intonation": 1.2}),
    "quote": ([("Voidoll", []), ("†聖騎士 紅桜†", []), ("ちび式じい", [])], [
        "あなたがロボットではないことを、証明してください。",
        "……侵入成功。",
        "昔は、パスワードなんて、なかったんじゃ。",
    ], {"speed": 1.0, "intonation": 1.0}),
}
ANNOUNCER = {"voice": "ja-JP-Chirp3-HD-Kore", "speed": 1.1, "pitch": 1.0, "af": "", "gain_db": -6, "prompt": ""}
NUMS = "いち に さん よん ご ろく なな はち きゅう じゅう".split()


def clip(text, s, backend, out):
    synth.process(synth.synth_raw(text, s, backend), out, s, backend)
    return synth.read_pcm(out)


def label(n, out):
    word = NUMS[n - 1] if n <= len(NUMS) else str(n)
    return clip(f"{word}ばん", ANNOUNCER, "chirp", out)


def build(role, all_styles):
    chars, lines, tune = ROLES[role]
    out_dir = ROOT / "build" / "compare"
    seg = out_dir / "vv_seg"
    seg.mkdir(parents=True, exist_ok=True)
    silence = lambda sec: array.array("h", bytes(2 * int(sec * RATE)))
    pcm, listing, n = array.array("h"), [], 0
    for ch, picks in chars:
        name = next(k for k in synth.vv_speakers() if k.replace(" ", "") == ch.replace(" ", ""))
        styles = [st for st, _ in synth.vv_speakers()[name]]
        if not all_styles:
            styles = picks or styles[:1]
        for style in styles:
            n += 1
            s = {"voice": f"{ch}（{style}）", "character": ch, "style": style, "speed": tune["speed"], "vv_pitch": 0.0,
                 "intonation": tune["intonation"], "pitch": 1.0, "af": "", "gain_db": 0, "prompt": ""}
            pcm += label(n, seg / f"label_{n}.wav") + silence(0.5)
            for j, line in enumerate(lines):
                pcm += clip(synth.reading(line, CFG, "voicevox"), s, "voicevox", seg / f"{role}_{n}_{j}.wav") + silence(0.6)
            pcm += silence(0.8)
            others = "、".join(st for st, _ in synth.vv_speakers()[name])
            listing.append(f"{n} 番  {ch}（{style}）　ほかのスタイル：{others}")
    wav = out_dir / f"vv_{role}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    subprocess.run([synth.ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "192k", str(wav.with_suffix(".mp3"))], check=True)
    wav.unlink()
    (out_dir / f"vv_{role}.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
    print(f"vv_{role}: {len(pcm) / RATE:.1f} 秒")
    print("\n".join(listing))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for role in args or ROLES:
        build(role, "--all-styles" in sys.argv)


if __name__ == "__main__":
    main()
