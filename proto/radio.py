"""ほのぼの週刊ラジオ（docs/RADIO.md）の台本 1 本を動画にする（試作）。

    タイトル → ラジオブースで 4 人が話す（話題ごとに見出し）→ 締め

proto/synth.py が書き出したタイムライン（build/<台本>/timeline_voicevox.json。combo: radio）と音声に、
漫才と同じキャラの部品画像（build/art/sprites/male・female）を、机の後ろに並べて重ねる。

    python proto/radio.py r0001_1028                  # 丸ごと（build/anim/r0001_1028.mp4）
    python proto/radio.py r0001_1028 --from 40 --to 60
    python proto/radio.py r0001_1028 --frames 5,50    # 静止画で確かめる

  - 口：話し手ごとの声の大きさで開け閉め。話している人は少し大きく弾む
  - 字幕：画面の下に、声に合わせて字を少しずつ出す（漫才の吹き出しの代わり。YouTube の字幕は付けない）。「」@news（ニュースを読む所）は青
  - 見出し：台本の topic: の所で、真ん中に大きく出してから左上に小さく残す
"""
import argparse
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import synth
from render import (FONT, SUB_FONT, H, W, STYLE_COLOR, center_paste, clamp01, ease_out, mouth_track, pill, read_wav,
                    resample, reveal_count, scaled, text_img)

ROOT = Path(__file__).resolve().parent.parent
SP = ROOT / "build" / "art" / "sprites"
DESK_Y = 735          # 机の上の端
FACE_Y = 470          # 4 人の顔の高さをそろえる
SCALE = 0.82
# 並び（左から）：話し手, 部品のフォルダ, 部品の名前, 部品の中の顔の高さ, 横の位置, 字幕の名前の色
SEATS = [("A", "male", "boke", 337, 300), ("B", "male", "tsukkomi", 362, 760),
         ("D", "female", "tsukkomi", 425, 1170), ("C", "female", "boke", 512, 1620)]
WHO_COLOR = {"A": (70, 140, 110), "B": (60, 80, 150), "C": (110, 120, 170), "D": (220, 90, 150)}
COLORS = {**STYLE_COLOR, "news": (25, 85, 170)}
T_TITLE = 3.5
T_TAIL = 2.5          # 最後のあいさつのあと
TOPIC_BIG = 2.4       # 見出しを大きく出す秒
CAP_W, CAP_LINES = 1560, 2


def booth():
    """ラジオブースの背景（壁の吸音パネル・窓・ON AIR のランプ・番組名）。机とマイクは前に重ねる部品。"""
    bg = Image.new("RGBA", (W, H), (236, 214, 186, 255))
    d = ImageDraw.Draw(bg)
    for gx in range(0, W, 160):          # 吸音パネル
        for gy in range(0, DESK_Y, 160):
            shade = 222 if (gx // 160 + gy // 160) % 2 else 214
            d.rounded_rectangle((gx + 8, gy + 8, gx + 152, gy + 152), radius=14, fill=(shade, shade - 26, shade - 58, 255))
            for k in range(4):
                y = gy + 30 + k * 30
                d.line((gx + 24, y, gx + 136, y), fill=(shade - 18, shade - 44, shade - 74, 255), width=3)
    # 調整室の窓
    d.rounded_rectangle((620, 60, 1300, 330), radius=20, fill=(60, 66, 92, 255), outline=(90, 70, 60, 255), width=14)
    d.polygon([(660, 80), (760, 80), (640, 300), (640, 200)], fill=(90, 100, 130, 255))
    d.rectangle((700, 250, 1220, 318), fill=(40, 44, 60, 255))    # 向こうの卓
    for i in range(14):
        d.rectangle((720 + i * 35, 262, 740 + i * 35, 300), fill=(120, 130, 150, 255))
        d.ellipse((724 + i * 35, 270 + (i * 7) % 20, 736 + i * 35, 282 + (i * 7) % 20), fill=(240, 200, 90, 255))
    return bg


def desk():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, DESK_Y, W, H), fill=(150, 96, 60, 255))
    d.rectangle((0, DESK_Y, W, DESK_Y + 26), fill=(178, 120, 78, 255))
    d.line((0, DESK_Y, W, DESK_Y), fill=(90, 56, 36, 255), width=5)
    for _, _, _, _, x in SEATS:         # マイク（アームの先に、話す人の口の前）
        d.line((x + 190, DESK_Y, x + 190, DESK_Y - 60), fill=(60, 60, 66, 255), width=12)
        d.line((x + 190, DESK_Y - 60, x + 160, DESK_Y - 120), fill=(60, 60, 66, 255), width=10)
        d.rounded_rectangle((x + 130, DESK_Y - 200, x + 180, DESK_Y - 115), radius=24, fill=(40, 40, 46, 255), outline=(20, 20, 24, 255), width=4)
        for k in range(3):
            d.line((x + 138, DESK_Y - 180 + k * 20, x + 172, DESK_Y - 180 + k * 20), fill=(90, 90, 100, 255), width=3)
    # 番組名（机の前に貼る）
    sign = pill("ほのぼの週刊ラジオ", 52, (255, 248, 230, 255), (120, 60, 40, 255), pad=(40, 12))
    im.alpha_composite(sign, (int(W / 2 - sign.width / 2), DESK_Y + 40))
    return im


def on_air(lit):
    im = Image.new("RGBA", (300, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 299, 95), radius=16, fill=(200, 30, 40, 255) if lit else (110, 40, 44, 255), outline=(40, 20, 20, 255), width=6)
    t = text_img("ON AIR", 56, (255, 255, 255, 255) if lit else (200, 160, 160, 255), (0, 0, 0, 0), 0)
    im.alpha_composite(t, (150 - t.width // 2, 48 - t.height // 2))
    if lit:
        glow = Image.new("RGBA", (340, 136), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((10, 10, 330, 126), radius=30, fill=(255, 60, 60, 110))
        glow = glow.filter(ImageFilter.GaussianBlur(12))
        glow.alpha_composite(im, (20, 20))
        return glow
    return im


class Radio:
    def __init__(self, script):
        import json
        self.base = ROOT / "build" / script
        self.tl = json.loads((self.base / "timeline_voicevox.json").read_text(encoding="utf-8"))
        self.fps = self.tl["fps"]
        self.mouth = mouth_track(self.tl)
        self.bg, self.desk = booth(), desk()
        self.lamp = {True: on_air(True), False: on_air(False)}
        self.S = {}
        for who, folder, role, _, _ in SEATS:
            for m in ("open", "closed"):
                self.S[(who, m)] = scaled(Image.open(SP / folder / f"{role}_stand_{m}.png").convert("RGBA"), SCALE)
        self.font = ImageFont.truetype(SUB_FONT, 46)
        self.topics = self.tl.get("topics", [])
        self.topic_big = {tp["text"]: pill(tp["text"], 72, (255, 214, 64, 255), (42, 34, 48, 255), pad=(56, 22)) for tp in self.topics}
        self.topic_small = {tp["text"]: pill(tp["text"], 40, (255, 214, 64, 255), (42, 34, 48, 255), pad=(30, 10)) for tp in self.topics}
        self.title = text_img(self.tl.get("title") or "", 140, (255, 255, 255, 255), (42, 34, 48, 255), 12, max_w=1700)
        self.theme = pill(self.tl.get("theme") or "", 56, (255, 214, 64, 255), (42, 34, 48, 255))
        self.t_main = T_TITLE
        self.total = T_TITLE + self.tl["duration"] + T_TAIL
        self._wrap = {}

    def speaking(self, who, k):
        arr = self.mouth.get(who)
        return arr is not None and 0 <= k < len(arr) and bool(arr[k])

    def people(self, frame, t):
        k = int(t * self.fps)
        for i, (who, _, _, face, x) in enumerate(SEATS):
            talk = any(self.speaking(who, j) for j in range(k - 6, k + 1))   # 話している間（少し余韻）
            im = self.S[(who, "open" if self.speaking(who, k) else "closed")]
            bob = 3 * math.sin(t * 1.8 + i * 1.3) - (6 * abs(math.sin(t * 9)) if talk else 0)
            y = FACE_Y - face * SCALE + bob
            frame.alpha_composite(im, (int(x - im.width / 2), int(y)))

    def caption(self, frame, t, box=(120, 880, W - 120, 1050), font=None, n_lines=CAP_LINES, tri=True):
        """いま話しているセリフ（話し始めから言い終わって 0.6 秒まで）を、声に合わせて少しずつ出す。
        box・font・n_lines・tri（話し手を指す三角）はショートで変える。"""
        font = font or self.font
        cur = [ln for ln in self.tl["lines"] if ln["start"] <= t <= ln["end"] + 0.6]
        if not cur:
            return
        ln = cur[-1]
        segs = ln["segs"] if ln["who"] != "ALL" else [sg for sg in ln["segs"] if sg["who"] == "D"]
        shown = []
        for sg in segs:
            frac = 1.0 if t >= sg["end"] else max(0.0, (t - sg["start"]) / max(0.01, sg["end"] - sg["start"])) if t >= sg["start"] else 0.0
            col = COLORS.get(sg["style"], (42, 34, 48))
            shown += [(ch, col) for ch in sg["text"][:reveal_count(sg["text"], frac)]]
        lines, cur_l, w = [], [], 0.0
        for ch, col in shown:
            cw = font.getlength(ch)
            if cur_l and w + cw > box[2] - box[0] - 70 and ch not in "、。！？」…ー":
                lines.append(cur_l)
                cur_l, w = [], 0.0
            cur_l.append((ch, col))
            w += cw
        if cur_l:
            lines.append(cur_l)
        lines = lines[-n_lines:]
        d = ImageDraw.Draw(frame)
        x0, y0, x1, y1 = box
        lh = int(font.size * 1.4)
        d.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=(255, 255, 255, 235), outline=(42, 34, 48, 255), width=5)
        seat = [s for s in SEATS if s[0] == (ln["who"] if ln["who"] in "ABCD" else "D")][0]
        tag_c = WHO_COLOR[seat[0]] if ln["who"] != "ALL" else (120, 90, 60)
        if tri:
            d.polygon([(seat[4] - 26, y0 + 3), (seat[4] + 26, y0 + 3), (seat[4], y0 - 30)], fill=tag_c)   # 誰のセリフかを指す三角
        d.rectangle((x0 + 3, y0 + 20, x0 + 16, y1 - 20), fill=tag_c)
        y = y0 + (y1 - y0 - lh * len(lines)) // 2 + 4
        for line in lines:
            xx = x0 + 44
            for ch, col in line:
                d.text((xx, y), ch, font=font, fill=col + (255,))
                xx += font.getlength(ch)
            y += lh

    def topic(self, frame, t):
        now = [tp for tp in self.topics if tp["start"] - 0.3 <= t]
        if not now:
            return
        tp = now[-1]
        u = t - (tp["start"] - 0.3)
        if u < TOPIC_BIG:
            s = 0.7 + 0.3 * ease_out(clamp01(u / 0.3))
            fade = clamp01((TOPIC_BIG - u) / 0.3)
            im = scaled(self.topic_big[tp["text"]], s)
            if fade < 1:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda a: int(a * fade)))
            center_paste(frame, im, W / 2, 470)
        else:
            im = self.topic_small[tp["text"]]
            v = ease_out(clamp01((u - TOPIC_BIG) / 0.3))
            frame.alpha_composite(im, (int(40 - (1 - v) * 600), 40))

    def frame(self, T, n, caption=True):
        if T < T_TITLE:
            frame = Image.alpha_composite(self.bg, Image.new("RGBA", (W, H), (20, 12, 36, 150)))
            u = clamp01((T - 0.2) / 0.35)
            if u > 0:
                center_paste(frame, scaled(self.title, 0.6 + 0.5 * ease_out(u) - 0.1 * clamp01((T - 0.55) / 0.2)), W / 2, H / 2 + 40)
            center_paste(frame, self.theme, W / 2 - (1 - ease_out(clamp01(T / 0.3))) * 900, H / 2 - 150)
            fade = clamp01((T - (T_TITLE - 0.4)) / 0.4)
            if fade:
                frame = Image.blend(frame, self.room(0.0), fade)
            return frame
        t = T - self.t_main
        frame = self.room(t)
        if t <= self.tl["duration"]:
            self.topic(frame, t)
            if caption:
                self.caption(frame, t)
        else:
            frame = Image.blend(frame, Image.new("RGBA", (W, H), (20, 12, 36, 255)), clamp01((t - self.tl["duration"] - 1.0) / (T_TAIL - 1.0)))
        return frame

    def room(self, t):
        frame = self.bg.copy()
        lamp = self.lamp[t > 0 and int(t * 2) % 6 != 5]
        frame.alpha_composite(lamp, (1560 - (lamp.width - 300) // 2, 120 - (lamp.height - 96) // 2))
        self.people(frame, t)
        frame.alpha_composite(self.desk)
        return frame


def build_audio(r, rate):
    n = int(r.total * rate) + rate
    mix = np.zeros(n, dtype=np.float32)

    def put(x, at, gain=1.0):
        i = int(at * rate)
        x = x[:max(0, n - i)]
        mix[i:i + len(x)] += x * gain

    def load(name):
        x, sr = read_wav(ROOT / "assets" / "audio" / f"{name}.wav")
        return resample(x, sr, rate)
    deb = load("debayashi")
    voice, vr = read_wav(r.base / r.tl["audio"])
    put(deb[:int(T_TITLE * rate)] * np.minimum(1, (int(T_TITLE * rate) - np.arange(min(len(deb), int(T_TITLE * rate)))) / (0.8 * rate)), 0, 0.5)
    put(resample(voice, vr, rate), r.t_main)
    # 話している間の小さな BGM（出囃子をくり返す）と、見出しの合図
    loop_len = r.tl["duration"] + T_TAIL
    loop = np.tile(deb, int(loop_len * rate / len(deb)) + 2)[:int(loop_len * rate)]
    loop *= np.minimum(1, (len(loop) - np.arange(len(loop))) / (2.0 * rate)) * np.minimum(1, np.arange(len(loop)) / (1.0 * rate))
    put(loop, r.t_main, 0.05)
    sting = deb[:int(1.2 * rate)] * np.minimum(1, (int(1.2 * rate) - np.arange(int(1.2 * rate))) / (0.4 * rate))
    for tp in r.topics:
        put(sting, r.t_main + tp["start"] - 1.1, 0.3)
    return np.clip(mix[:int(r.total * rate)], -1, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=None)
    ap.add_argument("--frames")
    args = ap.parse_args()
    r = Radio(args.script)
    out_dir = ROOT / "build" / "anim"
    if args.frames:
        (out_dir / "frames").mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(float(x) for x in args.frames.split(",")):
            png = out_dir / "frames" / f"{args.script}_{t:g}.png"
            r.frame(t, i).convert("RGB").save(png)
            print(png)
        return
    rate = 24000
    mix = build_audio(r, rate)
    t_from, t_to = args.t_from, min(args.t_to or r.total, r.total)
    stem = args.script + ("" if (t_from, args.t_to) == (0.0, None) else f"_{t_from:g}-{t_to:g}")
    wav = out_dir / f"{stem}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(mix[int(t_from * rate):int(t_to * rate)], -1, 1) * 32767).astype("<i2").tobytes())
    mp4 = out_dir / f"{stem}.mp4"
    fps = r.fps
    enc = subprocess.Popen([synth.ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(wav),
                            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-g", str(fps // 2), "-bf", "2",
                            "-af", "alimiter=limit=0.89:level=disabled",
                            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    for f in range(int((t_to - t_from) * fps)):
        t = t_from + f / fps
        enc.stdin.write(r.frame(t, f).convert("RGB").tobytes())
        if f % (fps * 30) == 0:
            print(f"  {t:6.1f} 秒")
    enc.stdin.close()
    enc.wait()
    wav.unlink()
    print(mp4, f"{t_to - t_from:.1f} 秒")


if __name__ == "__main__":
    main()
