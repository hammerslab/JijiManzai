"""ショート動画（縦 1080x1920）を作る。本編の頭のほうを切り出し、最後に「続きは本編で」のカードを付ける。

    python proto/short.py dopagaki                 # 書き出す
    python proto/short.py dopagaki --frames 3,20   # 動画にせず、その秒のコマを静止画で（確かめる用）

できるもの：build/anim/<台本>_short.mp4
区間：台本の頭の「short: 秒-秒」（漫才の頭からの秒）。なければ、あいさつの次の行から 2 回目の叩くツッコミの行の終わりまで（55 秒まで）。
画面：上に【ほのぼの漫才】の札・お題・題名、真ん中に舞台（吹き出しなし）、下に今のセリフを大きく（声に合わせて字を出す。ネタバレしない）。
右と下の端は YouTube の操作ボタンがかぶるので空ける。
"""
import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import render
import synth
from render import LEVELS, ROOT, Scene, pill, reveal_count, text_img

SW, SH = 1080, 1920
MAX_LEN = 55.0       # ショートの本編部分の長さの上限（秒）
CARD = 3.0           # 最後のカード
STAGE_Y = 520        # 舞台の上の y
TEXT_BOX = (50, 1190, 960, 1600)   # セリフの枠（右の 120px と下の 320px は空ける）
LINE_FONT = ImageFont.truetype(render.SUB_FONT, 58)
NAME = {"male": {"A": "ボケ", "B": "ツッコミ"}, "female": {"A": "ボケ", "B": "ツッコミ"}}
WHO_COLOR = {"A": (70, 150, 140), "B": (60, 80, 150)}
# 舞台は 2 人に寄って切り出す（縦の画面では小さく見えるため）：(上の y, 下の y)。横は 16:9 になるよう 2 人の真ん中から
CROP = {"male": (100, 930), "female": (250, 960)}


def pick_range(tl):
    if tl.get("short"):
        a, b = (float(x) for x in tl["short"].split("-"))
        return a, b
    lines = tl["lines"]
    start = lines[1]["start"] - 0.3 if len(lines) > 1 else 0.0
    hit_lines = [ln for ln in lines if ln["hit"]]
    end = hit_lines[1]["end"] + 0.6 if len(hit_lines) > 1 else (hit_lines[0]["end"] + 0.6 if hit_lines else start + MAX_LEN)
    if end - start > MAX_LEN:
        end = hit_lines[0]["end"] + 0.6 if hit_lines else start + MAX_LEN
    return max(0.0, start), min(end, start + MAX_LEN, tl["duration"])


class Short:
    def __init__(self, name):
        self.sc = Scene(name)
        tl = self.sc.tl
        self.a, self.b = pick_range(tl)
        self.total = (self.b - self.a) + CARD
        bg = Image.new("RGBA", (SW, SH), (28, 16, 48, 255))
        d = ImageDraw.Draw(bg)
        for y in range(SH):   # 上から下へ少し明るく
            c = int(16 + 30 * y / SH)
            d.line([(0, y), (SW, y)], fill=(28 + c // 2, 16 + c // 3, 48 + c, 255))
        title_y = 250
        badge = pill("ほのぼの漫才", 50, (230, 40, 60, 255), (255, 255, 255, 255), pad=(30, 12), font=render.SUB_FONT)
        bg.alpha_composite(badge, (50, 120))
        if tl.get("theme"):
            tp = pill(f"お題：{tl['theme']}", 40, (255, 214, 64, 255), (42, 34, 48, 255), pad=(24, 10), font=render.SUB_FONT)
            if 50 + badge.width + 20 + tp.width <= SW - 40:
                bg.alpha_composite(tp, (50 + badge.width + 20, 128))
            else:   # 長いお題は札の下に
                bg.alpha_composite(tp, (50, 120 + badge.height + 12))
                title_y = 120 + badge.height + 12 + tp.height + 20
        title = text_img(tl.get("title", name), 84, (255, 255, 255, 255), (30, 20, 40, 255), 10, render.FONT, max_w=SW - 140)
        bg.alpha_composite(title, (50, title_y))
        self.bg = bg
        self.card_title = text_img("続きは本編で ▶", 96, (255, 226, 60, 255), (30, 20, 40, 255), 12, render.SUB_FONT, max_w=SW - 140)
        self.card_sub = text_img("下の「関連動画」から", 56, (255, 255, 255, 255), (30, 20, 40, 255), 8, render.SUB_FONT)

    def stage(self, frame):
        """舞台を 2 人に寄って切り出し、横 1080 にする。"""
        y0, y1 = CROP[self.sc.combo]
        w = (y1 - y0) * 16 / 9
        mid = sum(self.sc.c["x"]) / 2
        x0 = max(0, min(render.W - w, mid - w / 2))
        return frame.crop((int(x0), y0, int(x0 + w), y1)).resize((SW, int(SW * 9 / 16)), Image.LANCZOS)

    def current_line(self, t):
        """いま話しているセリフ（話し手, 出す字）。声に合わせて少しずつ。"""
        for who in ("B", "A"):
            for start, end, parts in reversed(self.sc.bubbles.by[who]):
                if start <= t <= end + 0.6:
                    shown = ""
                    for a, b, text, _ in parts:
                        frac = 1.0 if t >= b else max(0.0, (t - a) / max(0.01, b - a)) if t >= a else 0.0
                        shown += text[:reveal_count(text, frac)]
                    return who, shown
        return None, ""

    def wrap(self, text, width):
        lines, cur = [], ""
        for ch in text:
            if cur and LINE_FONT.getlength(cur + ch) > width and not (ch in "、。！？」" and LINE_FONT.getlength(cur + ch) <= width + 40):
                lines.append(cur)
                cur = ""
            if not cur and ch == " ":
                continue
            cur += ch
        if cur:
            lines.append(cur)
        return lines

    def frame(self, T, n):
        out = self.bg.copy()
        if T < self.b - self.a:
            t = self.a + T
            stage = self.stage(self.sc.main_frame(t, n, bubbles=False))
            out.alpha_composite(stage, (0, STAGE_Y))
            who, text = self.current_line(t)
            if who:
                x0, y0, x1, y1 = TEXT_BOX
                d = ImageDraw.Draw(out)
                d.rounded_rectangle((x0, y0, x1, y1), radius=36, fill=(255, 255, 255, 245), outline=(42, 34, 48, 255), width=6)
                tag = pill(NAME[self.sc.combo][who], 40, WHO_COLOR[who] + (255,), (255, 255, 255, 255), pad=(22, 6), font=render.SUB_FONT)
                out.alpha_composite(tag, (x0 + 30, y0 - tag.height // 2))
                lines = self.wrap(text, x1 - x0 - 80)[-5:]
                y = y0 + 50
                for ln in lines:
                    d.text((x0 + 36, y), ln, font=LINE_FONT, fill=(42, 34, 48, 255))
                    y += 70
        else:   # 最後のカード
            stage = self.stage(self.sc.main_frame(self.b, n, bubbles=False))
            dark = Image.new("RGBA", stage.size, (0, 0, 0, 120))
            out.alpha_composite(Image.alpha_composite(stage.convert("RGBA"), dark), (0, STAGE_Y))
            out.alpha_composite(self.card_title, ((SW - self.card_title.width) // 2, 1250))
            out.alpha_composite(self.card_sub, ((SW - self.card_sub.width) // 2, 1400))
        return out

    def audio(self, rate=24000):
        sc = self.sc
        voice, vr = render.read_wav(sc.base / sc.tl["audio"])
        voice = render.resample(voice, vr, rate)
        mix = np.zeros(int(self.total * rate) + rate, dtype=np.float32)
        seg = voice[int(self.a * rate):int(self.b * rate)]
        mix[:len(seg)] += seg
        for h, lv in zip(sc.tl["hits"], sc.levels):
            if self.a <= h < self.b:
                name, gain = LEVELS[lv]["sfx"]
                x, r = render.read_wav(ROOT / "assets" / "audio" / f"{name}.wav")
                x = render.resample(x, r, rate) * gain
                i = int((h - self.a - 0.03) * rate)
                mix[i:i + len(x)] += x[:len(mix) - i]
        deb, r = render.read_wav(ROOT / "assets" / "audio" / "debayashi.wav")
        deb = render.resample(deb, r, rate)[:int(CARD * rate)]
        deb *= np.minimum(1, (len(deb) - np.arange(len(deb))) / (0.6 * rate))
        i = int((self.b - self.a) * rate)
        mix[i:i + len(deb)] += deb * 0.45
        return np.clip(mix[:int(self.total * rate)], -1, 1), rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--frames")
    args = ap.parse_args()
    sh = Short(args.script)
    out_dir = ROOT / "build" / "anim"
    if args.frames:
        (out_dir / "frames").mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(float(x) for x in args.frames.split(",")):
            png = out_dir / "frames" / f"{args.script}_short_{t:g}.png"
            sh.frame(t, i).convert("RGB").save(png)
            print(png)
        return
    mix, rate = sh.audio()
    wav = out_dir / f"{args.script}_short.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    mp4 = out_dir / f"{args.script}_short.mp4"
    fps = sh.sc.fps
    enc = subprocess.Popen([synth.ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{SW}x{SH}", "-r", str(fps), "-i", "-", "-i", str(wav),
                            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-g", str(fps // 2), "-bf", "2",
                            "-af", "alimiter=limit=0.89:level=disabled", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                            "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    for f in range(int(sh.total * fps)):
        enc.stdin.write(sh.frame(f / fps, f).convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    wav.unlink()
    print(mp4, f"{sh.total:.1f} 秒（本編の {sh.a:.1f}〜{sh.b:.1f} 秒）")


if __name__ == "__main__":
    main()
