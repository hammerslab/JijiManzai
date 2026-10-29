"""ほのぼの週刊ラジオのショート（縦 1080x1920、テレビ CM 風の予告。docs/RADIO.md）。

    python proto/radio_cm.py r0001_1028 "ブロッコリーです" "植木鉢の下" "マロンもこが気になります"
    python proto/radio_cm.py r0001_1028 ... --frames 3,20

  1. 頭：radio/<回>_cm.txt の声（「今週の、ほのぼの週刊ラジオは！」→ 話題を 1 つずつ）。言われた話題から下に並べていく
  2. 見どころ：本編から、引数の文を含むセリフの頭から、次のセリフ（ツッコミ）の終わりまでを切り出してつなぐ
  3. 締め：radio/<回>_cm_end.txt の声（「続きは、本編で！」）
声は synth.py で build/<回>_cm/ と build/<回>_cm_end/ に作っておく。できるもの：build/anim/<回>_short.mp4
"""
import argparse
import subprocess
import wave

import numpy as np
from PIL import Image, ImageFont

import radio
import render
import synth
from radio import ROOT, Radio
from render import center_paste, clamp01, ease_out, pill, read_wav, resample, scaled, text_img

SW, SH = 1080, 1920
ROOM_Y = 600            # 本編の画面（横長）を置く高さ
GAP = 0.4               # 区切りの間
CAP_BOX = (40, ROOM_Y + 640, SW - 120, ROOM_Y + 900)   # セリフの枠（右の 120px と下の 320px は YouTube のボタンのため空ける）
CAP_FONT = ImageFont.truetype(render.SUB_FONT, 54)


def find_clip(main, words):
    lines = main.tl["lines"]
    for i, ln in enumerate(lines):
        if words in ln["text"]:
            j = min(i + 1, len(lines) - 1)
            return ln["start"] - 0.3, lines[j]["end"] + 0.5
    raise SystemExit(f"本編に「{words}」がない")


class CM:
    def __init__(self, ep, picks):
        self.main = Radio(ep)
        self.head = Radio(f"{ep}_cm")
        self.tail = Radio(f"{ep}_cm_end")
        self.clips = [find_clip(self.main, w) for w in picks]
        self.t_clips = self.head.tl["duration"] + GAP
        self.t_tail = self.t_clips + sum(b - a for a, b in self.clips) + GAP
        self.total = self.t_tail + self.tail.tl["duration"] + 1.0
        self.badge = pill("ほのぼの週刊ラジオ", 64, (255, 248, 230, 255), (120, 60, 40, 255), pad=(44, 16))
        self.sub = pill("今週の話題", 48, (255, 214, 64, 255), (42, 34, 48, 255), pad=(34, 12))
        # 話題の一覧（頭の声で、2 行目以降の話し手のセリフが言われた順に出す）
        topics = [tp["text"].split("　", 1)[-1] for tp in self.main.topics]
        starts = [ln["start"] for ln in self.head.tl["lines"][1:]]
        self.items = [(starts[min(k, len(starts) - 1)], text_img(f"{k + 1}. {t}", 52, (42, 34, 48, 255), (255, 255, 255, 255), 6, max_w=880))
                      for k, t in enumerate(topics)]
        self.clip_label = pill("本編より", 44, (230, 40, 60, 255), (255, 255, 255, 255), pad=(30, 10))
        self.end_text = text_img("続きは本編で！", 110, (255, 255, 255, 255), (42, 34, 48, 255), 10)
        self.bg = Image.new("RGBA", (SW, SH), (236, 214, 186, 255))

    def room(self, f, r, t):
        """横長の画面を縮めて置き、その下にいまのセリフを大きく出す。"""
        im = r.frame(radio.T_TITLE + t, 0, caption=False).convert("RGB").resize((SW, int(SW * 9 / 16)), Image.BILINEAR)
        f.paste(im, (0, ROOM_Y))
        r.caption(f, t, box=CAP_BOX, font=CAP_FONT, n_lines=3, tri=False)

    def frame(self, T):
        f = self.bg.copy()
        center_paste(f, self.badge, SW / 2, 150)
        if T < self.t_clips:                       # 頭
            self.room(f, self.head, T)
            for k, (a, im) in enumerate(self.items):
                u = clamp01((T - a) / 0.25)
                if u > 0:
                    f.alpha_composite(im, (int(80 - (1 - ease_out(u)) * 900), 230 + k * 80))
        elif T < self.t_tail:                       # 見どころ
            u = T - self.t_clips
            for a, b in self.clips:
                if u < b - a:
                    self.room(f, self.main, a + u)
                    break
                u -= b - a
            f.alpha_composite(self.clip_label, (40, ROOM_Y - 90))
        else:                                       # 締め
            t = T - self.t_tail
            self.room(f, self.tail, t)
            s = 0.6 + 0.4 * ease_out(clamp01(t / 0.3))
            center_paste(f, scaled(self.end_text, s), SW / 2, ROOM_Y - 160)
        return f

    def audio(self, rate):
        n = int(self.total * rate) + rate
        mix = np.zeros(n, dtype=np.float32)

        def put(x, at, gain=1.0):
            i = int(at * rate)
            x = x[:max(0, n - i)]
            mix[i:i + len(x)] += x * gain

        def voice(r):
            x, sr = read_wav(r.base / r.tl["audio"])
            return resample(x, sr, rate)
        put(voice(self.head), 0)
        mv = voice(self.main)
        at = self.t_clips
        for a, b in self.clips:
            seg = mv[int(a * rate):int(b * rate)].copy()
            k = int(0.15 * rate)
            seg[:k] *= np.linspace(0, 1, k)
            seg[-k:] *= np.linspace(1, 0, k)
            put(seg, at)
            at += b - a
        put(voice(self.tail), self.t_tail)
        deb, sr = read_wav(ROOT / "assets" / "audio" / "debayashi.wav")
        deb = resample(deb, sr, rate)
        loop = np.tile(deb, int(self.total * rate / len(deb)) + 2)[:int(self.total * rate)]
        loop *= np.minimum(1, (len(loop) - np.arange(len(loop))) / (1.0 * rate))
        put(loop, 0, 0.08)
        return np.clip(mix[:int(self.total * rate)], -1, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("picks", nargs="+", help="見どころにするセリフの一部（本編の台本の字）")
    ap.add_argument("--frames")
    args = ap.parse_args()
    cm = CM(args.ep, args.picks)
    out_dir = ROOT / "build" / "anim"
    if args.frames:
        for t in (float(x) for x in args.frames.split(",")):
            png = out_dir / "frames" / f"{args.ep}_short_{t:g}.png"
            cm.frame(t).convert("RGB").save(png)
            print(png)
        return
    rate, fps = 24000, 30
    wav = out_dir / f"{args.ep}_short.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((cm.audio(rate) * 32767).astype("<i2").tobytes())
    mp4 = out_dir / f"{args.ep}_short.mp4"
    enc = subprocess.Popen([synth.ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{SW}x{SH}", "-r", str(fps), "-i", "-", "-i", str(wav),
                            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-g", str(fps // 2), "-bf", "2",
                            "-af", "alimiter=limit=0.89:level=disabled",
                            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    for f in range(int(cm.total * fps)):
        enc.stdin.write(cm.frame(f / fps).convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    wav.unlink()
    print(mp4, f"{cm.total:.1f} 秒")


if __name__ == "__main__":
    main()
