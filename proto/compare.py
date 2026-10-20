"""声の候補の聴き比べ。候補ごとに「n 番」と案内してから、同じセリフを続けて読む。

    python proto/compare.py female_boke female_tsukkomi   # 組の名前は SETS のキー

できるもの：build/compare/<組>.mp3 と、何番が何の声かの <組>.txt
"""
import array
import sys
import subprocess
import wave

import synth
from synth import RATE, ROOT

# 聴き比べの組：名前 → (読ませるセリフ, 候補)。候補は (名前, 声, 速さ, 高さ, 音量 dB)
SETS = {
    "tsukkomi": ([
        "ただの導通確認やないか！ ネット繋がってるか確かめただけだろ！",
        "お前がやれよ！ 人間であることを証明するテストをAIにやらせてどうするんだよ！",
        "しょーもな！ 誰でも開ける共有フォルダに入ってるやつだろ！",
    ], [
        ("いまの声（Sadachbia）", "ja-JP-Chirp3-HD-Sadachbia", 1.08, 1.0, 0),
        ("Sadachbia を速く・高く・大きく", "ja-JP-Chirp3-HD-Sadachbia", 1.2, 1.05, 1.5),
        ("Fenrir", "ja-JP-Chirp3-HD-Fenrir", 1.15, 1.0, 1.5),
        ("Orus", "ja-JP-Chirp3-HD-Orus", 1.15, 1.0, 1.5),
        ("Alnilam", "ja-JP-Chirp3-HD-Alnilam", 1.15, 1.0, 1.5),
        ("Iapetus", "ja-JP-Chirp3-HD-Iapetus", 1.15, 1.0, 1.5),
        ("Zubenelgenubi", "ja-JP-Chirp3-HD-Zubenelgenubi", 1.15, 1.0, 1.5),
        ("Rasalgethi", "ja-JP-Chirp3-HD-Rasalgethi", 1.15, 1.0, 1.5),
    ]),
    # 女性コンビのボケ：低めで落ち着いた声
    "female_boke": ([
        "いきなりなんだけどさ、あたし、ハッカーになろうと思うんだよね。",
        "いや、画面の隅にある、パスワードを忘れた方はこちら、をクリックした。",
        "会社の、共有冷蔵庫のプリン管理台帳、エクセルファイルだ。",
    ], [
        ("Sulafat", "ja-JP-Chirp3-HD-Sulafat", 1.05, 0.97, 1.5),
        ("Gacrux", "ja-JP-Chirp3-HD-Gacrux", 1.05, 1.0, 1.5),
        ("Vindemiatrix", "ja-JP-Chirp3-HD-Vindemiatrix", 1.05, 1.0, 1.5),
        ("Achernar", "ja-JP-Chirp3-HD-Achernar", 1.05, 0.97, 1.5),
        ("Despina", "ja-JP-Chirp3-HD-Despina", 1.05, 0.97, 1.5),
        ("Erinome", "ja-JP-Chirp3-HD-Erinome", 1.05, 0.97, 1.5),
    ]),
    # 女性コンビのツッコミ：高めの声
    "female_tsukkomi": ([
        "ただの導通確認やないか！ ネット繋がってるか確かめただけだろ！",
        "お前がやれよ！ 人間であることを証明するテストをAIにやらせてどうするんだよ！",
        "しょーもな！ 誰でも開ける共有フォルダに入ってるやつだろ！",
    ], [
        ("Leda", "ja-JP-Chirp3-HD-Leda", 1.12, 1.05, 1.5),
        ("Zephyr", "ja-JP-Chirp3-HD-Zephyr", 1.12, 1.05, 1.5),
        ("Autonoe", "ja-JP-Chirp3-HD-Autonoe", 1.12, 1.05, 1.5),
        ("Laomedeia", "ja-JP-Chirp3-HD-Laomedeia", 1.12, 1.05, 1.5),
        ("Aoede", "ja-JP-Chirp3-HD-Aoede", 1.12, 1.05, 1.5),
        ("Callirrhoe", "ja-JP-Chirp3-HD-Callirrhoe", 1.12, 1.05, 1.5),
    ]),
}
ANNOUNCER = {"voice": "ja-JP-Chirp3-HD-Kore", "speed": 1.1, "pitch": 1.0, "af": "", "gain_db": -6, "prompt": ""}
NUMS = "いち に さん よん ご ろく なな はち".split()


def clip(text, s, out):
    synth.process(synth.synth_raw(text, s, "chirp"), out, s, "chirp")
    return synth.read_pcm(out)


def build(name):
    lines, candidates = SETS[name]
    out_dir = ROOT / "build" / "compare"
    seg = out_dir / "seg"
    seg.mkdir(parents=True, exist_ok=True)
    pcm = array.array("h")
    silence = lambda sec: array.array("h", bytes(2 * int(sec * RATE)))
    listing = []
    for n, (label, voice, speed, pitch, gain) in enumerate(candidates, 1):
        pcm += clip(f"{NUMS[n - 1]}ばん", ANNOUNCER, seg / f"label_{n}.wav") + silence(0.6)
        s = {"voice": voice, "speed": speed, "pitch": pitch, "af": "", "gain_db": gain, "prompt": ""}
        for j, line in enumerate(lines):
            pcm += clip(line, s, seg / f"{name}_{n}_{j}.wav") + silence(0.7)
        pcm += silence(0.8)
        listing.append(f"{n} 番  {label}（速さ {speed}・高さ {pitch}・音量 +{gain}dB）")
    wav = out_dir / f"{name}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    subprocess.run([synth.ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "192k",
                    str(wav.with_suffix(".mp3"))], check=True)
    (out_dir / f"{name}.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
    print(f"{name}: {len(pcm) / RATE:.1f} 秒")


def main():
    for name in sys.argv[1:] or SETS:
        build(name)


if __name__ == "__main__":
    main()
