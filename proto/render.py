"""台本 1 本を、決まった形の動画にする。

    タイトル（題名とお題）→ 2 人が袖から登場 → 漫才（3 分以内）→ 2 人が袖へ退場 → エンディング（名場面を流しながら、2 人の声でチャンネル登録を頼む）

proto/synth.py が書き出したタイムライン（build/<台本>/timeline_chirp.json）と音声に、部品画像（art/gen_chars.py）を重ねる。
エンディングの声は、コンビごとに決まった台本（proto/ending_male.txt / ending_female.txt）を synth.py で作っておく。

    python proto/render.py chappy                     # 丸ごと
    python proto/render.py chappy --from 0 --to 12    # 一部だけ（秒は動画の頭から。確かめる用）
    python proto/render.py chappy --main-only         # 漫才の部分だけ（--from/--to は漫才の頭から）
    python proto/render.py chappy --frames 5,40.2     # 動画にせず、その秒のコマを静止画で書き出す（確かめる用）
    python proto/render.py chappy --backend voicevox  # どの声で作ったタイムラインを使うか（省くと VOICEVOX があればそれ）

できるもの：build/anim/<台本>.mp4（一部だけのときは <台本>_<from>-<to>.mp4、漫才だけのときは <台本>_main.mp4）

漫才の部分の動き：
  - 口：話し手ごとの声の大きさで開け閉め（重なったところは 2 人とも動く）
  - 吹き出し：話している人の吹き出しに、声に合わせて字を少しずつ出す（言い終わる前にオチの字が見えないように）。
    「」で声を変えた所は字の色を変える。YouTube の字幕は付けない（docs/VIDEO_GUIDE.md）
  - 叩くツッコミ（台本の B! / B!! / B!!!）：声の頭で手刀が当たり、効果音・当たりの星・画面の揺れ。強さで大きさが変わる。
    男のボケは腰から「く」の字に折れ（25°／42°／60°）、女のボケは両手を上げて飛ばされてから戻ってくる（遠さ・高さ・傾きが変わり、いちばん強いと回る）
  - 締めの「どうも、ありがとうございましたー！」から、小さめの拍手が退場まで続く
  - 見つめ合う（台本の「(見つめ合う 秒)」）：黙っている間と次のセリフのあいだ、2 人とも相手を見て、少し相手のほうへ傾く
  - 待っている間も、2 人とも少しだけ上下に揺れる
"""
import argparse
import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import synth

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080
FLOOR_Y = 930
FEET = (500, 960)                      # 部品画像の中の足元
COMBOS = {   # art/gen_chars.py の COMBOS と同じ立ち位置。head＝頭の位置（足元から）、bubble＝吹き出しの真ん中の x と上の y（顔にかからない外側）
    "male": {"x": (770, 1165), "hand": (-320, -468), "head": {"A": (0, -655), "B": (0, -615)},
             "bubble": {"A": (400, 150), "B": (1565, 160)}},
    "female": {"x": (790, 1140), "hand": (-294, -352), "head": {"A": (0, -450), "B": (0, -546)},
               "bubble": {"A": (430, 250), "B": (1525, 230)}},
}
# 叩く強さ（台本の ! の数）ごとの動き。knock＝女のボケが飛ぶ（距離, 高さ, 傾き, 回転）、bend＝男のボケの絵、
# hold＝飛んだ・折れたままの秒、back＝戻る秒、fx＝当たりの星の大きさ、shake＝画面の揺れ、sfx＝効果音とその音量
LEVELS = {
    1: {"knock": (40, 25, 8, 0), "bend": "boke_hit1_open", "hold": 0.45, "back": 0.35, "fx": 0.8, "shake": 4, "sfx": ("pashi", 0.7)},
    2: {"knock": (70, 42, 14, 0), "bend": "boke_hit_open", "hold": 0.55, "back": 0.45, "fx": 1.0, "shake": 8, "sfx": ("slap", 0.7)},
    3: {"knock": (130, 70, 25, 360), "bend": "boke_hit3_open", "hold": 0.8, "back": 0.6, "fx": 1.35, "shake": 14, "sfx": ("slap", 1.0)},
}
FLY = 0.35          # 女のボケが飛んでいる秒
APPLAUSE_GAIN = 0.3  # 締めのあいさつの拍手（控えめ）
BUBBLE_W = 440       # 吹き出しの字の幅
BUBBLE_LINES = 4     # 吹き出しに出す行数（多いときは新しい行だけ）
BUBBLE_HOLD = 0.8    # 言い終わってから吹き出しを残す秒（相手が話し始めて 0.3 秒たったら消す）
STYLE_COLOR = {"robot": (31, 111, 209), "system": (31, 111, 209), "shibui": (150, 30, 60), "jii": (120, 80, 30),
               "chappy": (110, 60, 170), "polite": (110, 60, 170), "cute": (220, 60, 130), "whisper": (120, 120, 120)}
LEAN = 2.5          # 見つめ合うときに相手のほうへ傾ける角度
LOOK_EASE = 0.25    # 傾きを付ける・戻すのにかける秒数

# 決まった形の長さ（秒）
T_TITLE = 3.5       # タイトル
T_IN = 3.3          # 袖から登場（歩くのは 3.0 秒）
T_OUT = 3.0         # 袖へ退場
END_PAD = 1.0       # エンディングの声のあとに残す秒
CLIP_BEFORE, CLIP_AFTER = 2.5, 1.5   # エンディングの名場面：叩くツッコミの前後の秒
WING_X = 2150       # 袖（画面の右の外）
FONT = ROOT / "assets" / "fonts" / "ZenMaruGothic-Medium.ttf"
SUB_FONT = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    return x, rate


def resample(x, src, dst):
    if src == dst:
        return x
    n = int(len(x) * dst / src)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def ease_out(u):
    return 1 - (1 - u) ** 3


def ease_in_out(u):
    return 3 * u * u - 2 * u * u * u


def clamp01(u):
    return max(0.0, min(1.0, u))


def look_amount(t, looks):
    """見つめ合いの度合い（0〜1）。始まりと終わりは LOOK_EASE 秒かけてなめらかに。"""
    best = 0.0
    for a, b in looks:
        if a - LOOK_EASE < t < b + LOOK_EASE:
            u = min((t - a) / LOOK_EASE + 1, (b - t) / LOOK_EASE + 1, 1.0)
            best = max(best, ease_in_out(max(0.0, u)))
    return best


def mouth_track(tl):
    """話し手ごとに、声の大きさが「その人のよく出る大きさ」の 35% を超えたコマで口を開ける。"""
    out = {}
    for who, arr in tl["mouth"].items():
        a = np.array(arr)
        voiced = a[a > 0.01]
        thr = 0.35 * np.percentile(voiced, 90) if len(voiced) else 1.0
        out[who] = a > thr
    return out


def text_img(text, size, fill, stroke, stroke_w, font=FONT, max_w=None):
    """縁取りつきの文字を、透明な画像にする。max_w を超えるときは字を小さくする。"""
    f = ImageFont.truetype(str(font), size)
    while max_w and f.getlength(text) > max_w and size > 20:
        size -= 4
        f = ImageFont.truetype(str(font), size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke_w)
    im = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - l, 2 - t), text, font=f, fill=fill, stroke_width=stroke_w, stroke_fill=stroke)
    return im


def caption_img(text, size, fill, max_w):
    """字幕。1 行に入らないときは、真ん中に近い句読点で 2 行に分ける（字を小さくしない）。"""
    f = ImageFont.truetype(SUB_FONT, size)
    lines = [text]
    if f.getlength(text) > max_w:
        cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "！？。、 "]
        if cuts:
            i = min(cuts, key=lambda i: abs(i - len(text) / 2))
            lines = [text[:i].strip(), text[i:].strip()]
    ims = [text_img(ln, size, fill, (42, 34, 48, 255), 7, SUB_FONT, max_w=max_w) for ln in lines]
    out = Image.new("RGBA", (max(im.width for im in ims), sum(im.height for im in ims) + 6 * (len(ims) - 1)), (0, 0, 0, 0))
    y = 0
    for im in ims:
        out.alpha_composite(im, ((out.width - im.width) // 2, y))
        y += im.height + 6
    return out


def pill(text, size, bg, fg, pad=(36, 16), font=FONT):
    t = text_img(text, size, fg, fg, 0, font)
    w, h = t.width + pad[0] * 2, t.height + pad[1] * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg, outline=(42, 34, 48, 255), width=5)
    im.alpha_composite(t, (pad[0], pad[1]))
    return im


def scaled(im, s):
    return im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC) if s != 1 else im


def center_paste(frame, im, cx, cy):
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def reveal_count(text, frac):
    """声の進み具合（0〜1）に合わせて、何文字まで出すか。漢字は音が多いので重く、記号は軽く数える。"""
    w = [1.8 if "\u4e00" <= ch <= "\u9fff" else 0.5 if ch in "、。！？…「」 " else 1.0 for ch in text]
    total, acc = sum(w), 0.0
    for i, x in enumerate(w):
        acc += x
        if acc > frac * total + 1e-6:
            return i
    return len(text)


class Bubbles:
    """吹き出し。区切り（タイムラインの segs）ごとに、声の長さに合わせて字を少しずつ出す。"""

    def __init__(self, tl, combo):
        self.font = ImageFont.truetype(SUB_FONT, 38)
        self.c = COMBOS[combo]
        self.by = {"A": [], "B": []}   # 話し手ごと：[(最初の声の頭, 最後の声の終わり, [(頭, 終わり, 字, 色), ...])]
        for ln in tl["lines"]:
            for who in ("A", "B"):
                segs = [sg for sg in ln.get("segs", []) if sg["who"] == who]
                if not segs:
                    continue
                parts = []
                for i, sg in enumerate(segs):
                    text = sg["text"] + (" " if i == 0 and ln["hit"] and len(segs) > 1 else "")
                    parts.append((sg["start"], sg["end"], text, STYLE_COLOR.get(sg["style"], (42, 34, 48))))
                self.by[who].append((segs[0]["start"], segs[-1]["end"], parts))
        self._layout = {}

    def wrap(self, chars):
        """(字, 色) の並びを、幅に収まる行に分ける。"""
        lines, cur, width = [], [], 0.0
        for ch, col in chars:
            cw = self.font.getlength(ch)
            if cur and width + cw > BUBBLE_W and not (ch in "、。！？」…ー" and width + cw <= BUBBLE_W + 40):  # 句読点は行の頭に来ないよう前の行に残す
                lines.append(cur)
                cur, width = [], 0.0
            if not cur and ch == " ":
                continue
            cur.append((ch, col))
            width += cw
        if cur:
            lines.append(cur)
        return lines

    def draw(self, frame, t, xb, xt, shake=0):
        for who, x in (("A", xb), ("B", xt)):
            active = [b for b in self.by[who] if b[0] <= t <= b[1] + BUBBLE_HOLD]
            if not active:
                continue
            start, end, parts = active[-1]
            other = [b[0] for b in self.by["B" if who == "A" else "A"] if start < b[0] <= t]
            if other and t > end and t > other[-1] + 0.3:   # 相手が話し始めたら、言い終わった吹き出しは消す
                continue
            full = [(ch, col) for _, _, text, col in parts for ch in text]
            shown = []
            for a, b, text, col in parts:
                frac = 1.0 if t >= b else max(0.0, (t - a) / max(0.01, b - a)) if t >= a else 0.0
                shown += [(ch, col) for ch in text[:reveal_count(text, frac)]]
            key = (who, start)
            if key not in self._layout:
                self._layout[key] = min(BUBBLE_LINES, len(self.wrap(full)))
            n_lines = self._layout[key]
            lines = self.wrap(shown)[-n_lines:] if shown else []
            self.box(frame, who, x + shake, n_lines, lines)

    def box(self, frame, who, x, n_lines, lines):
        lh, pad = 50, 24
        w_box, h_box = BUBBLE_W + pad * 2, n_lines * lh + pad * 2 - 8
        cx, y0 = self.c["bubble"][who]
        x0 = int(cx - w_box / 2)
        x1, y1 = x0 + w_box, y0 + h_box
        hx, hy = self.c["head"][who]
        tip = (x + hx + (-60 if who == "A" else 60), FLOOR_Y + hy)
        side = x1 - 6 if who == "A" else x0 + 6
        base = [(side, y0 + h_box * 0.45), (side, y0 + h_box * 0.75)]
        d = ImageDraw.Draw(frame)
        outline, fill = (42, 34, 48, 255), (255, 255, 255, 240)
        d.polygon([base[0], tip, base[1]], fill=fill, outline=outline, width=5)
        d.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=fill, outline=outline, width=5)
        d.polygon([(base[0][0] + (-3 if who == "A" else 3), base[0][1] + 6), tip,
                   (base[1][0] + (-3 if who == "A" else 3), base[1][1] - 6)], fill=fill)   # しっぽの付け根の線を消す
        y = y0 + pad - 4
        for line in lines:
            xx = x0 + pad
            for ch, col in line:
                d.text((xx, y), ch, font=self.font, fill=col + (255,))
                xx += self.font.getlength(ch)
            y += lh


class Scene:
    """部品画像と漫才のタイムラインから、1 コマずつ絵を作る。"""

    def __init__(self, script, backend=None):
        self.base = ROOT / "build" / script
        if backend is None:   # VOICEVOX で作ってあればそれ、なければ Google の声
            backend = "voicevox" if (self.base / "timeline_voicevox.json").exists() else "chirp"
        self.backend = backend
        self.tl = json.loads((self.base / f"timeline_{backend}.json").read_text(encoding="utf-8"))
        self.levels = self.tl.get("hit_levels") or [2] * len(self.tl["hits"])   # 強さのない前のタイムラインは「強い」
        self.combo, self.fps = self.tl["combo"], self.tl["fps"]
        self.c = COMBOS[self.combo]
        sp = ROOT / "build" / "art" / "sprites"
        self.bg = Image.open(sp / self.combo / "bg.png").convert("RGBA")
        self.curtain = Image.open(sp / self.combo / "curtain_front.png").convert("RGBA")   # 左右の幕（袖）
        self.S = {f.stem: Image.open(f).convert("RGBA") for f in (sp / self.combo).glob("*_*.png") if f.stem != "curtain_front"}
        self.impact = Image.open(sp / "impact.png").convert("RGBA")
        shadow = Image.new("RGBA", (300, 60), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).ellipse((20, 10, 280, 50), fill=(0, 0, 0, 70))
        self.shadow = shadow.filter(ImageFilter.GaussianBlur(4))
        self.mouth = mouth_track(self.tl)
        self.bubbles = Bubbles(self.tl, self.combo)

    def paste(self, frame, sprite, x, dx=0.0, dy=0.0, rot=0.0, center=FEET):
        if rot:
            sprite = sprite.rotate(rot, resample=Image.BICUBIC, center=center)
        frame.paste(sprite, (int(x - FEET[0] + dx), int(FLOOR_Y - FEET[1] + dy)), sprite)  # 画面の外にはみ出してもよい

    def walkers(self, frame, xb, xt, phase_b, phase_t, moving_b, moving_t):
        """歩いている 2 人（口は閉じて正面）。歩いている間は弾んで左右に揺れる。"""
        for x, name, phase, moving in ((xb, "boke_stand_closed", phase_b, moving_b), (xt, "tsukkomi_stand_closed", phase_t, moving_t)):
            hop = -abs(math.sin(phase)) * 14 if moving else 0
            rot = 3 * math.sin(phase) if moving else 0
            frame.alpha_composite(self.shadow, (int(x - 150), FLOOR_Y - 26))
            self.paste(frame, self.S[name], x, 0, hop, rot)
        frame.alpha_composite(self.curtain)   # 袖の幕の後ろから出入りする

    def main_frame(self, t, frame_no):
        """漫才の部分の 1 コマ（t は漫才の頭からの秒）。"""
        c, tl, S = self.c, self.tl, self.S
        k = max(0, min(int(t * self.fps), len(self.mouth["A"]) - 1))
        near = min(range(len(tl["hits"])), key=lambda i: abs(t - tl["hits"][i]), default=None)   # いちばん近い叩くツッコミ
        tau = t - tl["hits"][near] if near is not None else 99.0
        lv = LEVELS[self.levels[near]] if near is not None else LEVELS[2]
        look = look_amount(t, tl["looks"])
        eyes = "_look" if look > 0.5 else ""
        shake = (lv["shake"] if frame_no % 2 else -lv["shake"]) if 0 <= tau < 0.12 else 0
        frame = self.bg.copy()
        if shake:
            frame.paste(self.bg, (shake, 0))
        bob_b = 2 * math.sin(t * 2.1)            # 待っている間の小さな揺れ（2 人で周期をずらす）
        bob_t = 2 * math.sin(t * 1.7 + 1.3)
        xb, xt = c["x"]

        # ボケ
        bdx, bdy, brot, pivot = 0.0, bob_b, -LEAN * look, FEET
        boke = S[f"boke_stand_{'open' if self.mouth['A'][k] else 'closed'}{eyes}"]
        if self.combo == "female":   # 飛ばされて、戻ってくる
            dist, height, tilt, spin = lv["knock"]
            if 0 <= tau < FLY:
                u = tau / FLY
                bdx, bdy, brot = -dist * ease_out(u), -height * 4 * u * (1 - u), (tilt + spin) * ease_out(u)
                boke = S["boke_hit_open"]
                if spin:   # 回るときは腰を中心に（足元を中心にすると床にめり込む）
                    pivot = (FEET[0], FEET[1] - 250)
            elif FLY <= tau < lv["hold"]:
                bdx, brot = -dist, tilt * (1 - (tau - FLY) / (lv["hold"] - FLY))
                boke = S["boke_hit_open"]
            elif lv["hold"] <= tau < lv["hold"] + lv["back"]:
                bdx = -dist * (1 - ease_in_out((tau - lv["hold"]) / lv["back"]))
        elif 0 <= tau < lv["hold"]:  # 腰から折れる（強さで角度が違う絵）
            boke = S[lv["bend"]]
            bdx, bdy = -14 * (1 - tau / lv["hold"]), 0.0
        frame.alpha_composite(self.shadow, (int(xb - 150 + bdx * 0.8 + shake), FLOOR_Y - 26))
        self.paste(frame, boke, xb + shake, bdx, bdy, brot, pivot)

        # ツッコミ（手刀を振り込んでから当てる）
        frame.alpha_composite(self.shadow, (int(xt - 150 + shake), FLOOR_Y - 26))
        tm = "open" if self.mouth["B"][k] else "closed"
        if -0.1 <= tau < 0.45:
            swing = 50 * (-tau / 0.1) if tau < 0 else 0
            self.paste(frame, S[f"tsukkomi_tsukkomi_{tm}"], xt + shake, swing)
        else:
            self.paste(frame, S[f"tsukkomi_stand_{tm}{eyes}"], xt + shake, 0, bob_t, LEAN * look)

        # 当たりの星
        if 0 <= tau < 0.2:
            s = (0.6 + 2.5 * tau) * lv["fx"]
            fx = self.impact.resize((int(320 * s), int(320 * s)), Image.BICUBIC)
            hx, hy = xt + c["hand"][0] + shake, FLOOR_Y + c["hand"][1]
            frame.alpha_composite(fx, (int(hx - fx.width / 2), int(hy - fx.height / 2)))

        # 吹き出し
        self.bubbles.draw(frame, t, xb, xt, shake)
        return frame


class Format:
    """タイトル → 登場 → 漫才 → 退場 → エンディング の並びと、それぞれの絵。"""

    def __init__(self, scene):
        self.sc = scene
        tl = scene.tl
        end_file = ROOT / "build" / f"ending_{scene.combo}" / f"timeline_{scene.backend}.json"
        if not end_file.exists():
            raise SystemExit(f"エンディングの声がない。python proto/synth.py proto/ending_{scene.combo}.txt --backend {scene.backend} で作る")
        self.end_tl = json.loads(end_file.read_text(encoding="utf-8"))
        self.end_mouth = mouth_track(self.end_tl)
        self.t_main = T_TITLE + T_IN
        self.t_out = self.t_main + tl["duration"]
        self.t_end = self.t_out + T_OUT
        self.total = self.t_end + 0.5 + self.end_tl["duration"] + END_PAD
        # タイトル
        dark = Image.new("RGBA", (W, H), (20, 12, 36, 150))
        self.title_bg = Image.alpha_composite(scene.bg, dark)
        self.theme_img = pill(f"お題：{tl.get('theme') or '？'}", 54, (255, 214, 64, 255), (42, 34, 48, 255))
        self.title_img = text_img(tl.get("title") or "", 128, (255, 255, 255, 255), (42, 34, 48, 255), 10, max_w=1700)
        # エンディング
        blur = scene.bg.filter(ImageFilter.GaussianBlur(10))
        self.end_bg = Image.alpha_composite(blur, Image.new("RGBA", (W, H), (20, 12, 36, 110)))
        self.label = pill("名場面", 44, (255, 214, 64, 255), (42, 34, 48, 255), pad=(30, 10))
        self.sub_btn = pill("チャンネル登録", 60, (230, 40, 60, 255), (255, 255, 255, 255), pad=(48, 18))
        self.sub_note = text_img("高評価・通知もよろしく！", 40, (255, 255, 255, 255), (42, 34, 48, 255), 6)
        self.end_chars = {k: scaled(v, 0.62) for k, v in scene.S.items() if k.startswith(("boke_stand", "tsukkomi_stand")) and "look" not in k}
        hits = tl["hits"]
        picks = [hits[i] for i in sorted({0, len(hits) // 2, len(hits) - 1})] if hits else [tl["duration"] / 2]
        self.clips = [(max(0.0, h - CLIP_BEFORE), min(tl["duration"], h + CLIP_AFTER)) for h in picks]
        self.captions = [(ln["start"], ln["end"], ln["who"], ln["text"]) for ln in self.end_tl["lines"]]
        self._cap_cache = {}

    def frame(self, T, n):
        sc = self.sc
        xb, xt = sc.c["x"]
        if T < T_TITLE:                                   # タイトル
            frame = self.title_bg.copy()
            u = clamp01((T - 0.2) / 0.35)
            if u > 0:
                s = 0.6 + 0.5 * ease_out(u) - 0.1 * clamp01((T - 0.55) / 0.2)   # ぽんと大きくなって少し戻る
                center_paste(frame, scaled(self.title_img, s), W / 2, H / 2 + 40)
            v = clamp01(T / 0.3)
            center_paste(frame, self.theme_img, W / 2 - (1 - ease_out(v)) * 900, H / 2 - 140)
            fade = clamp01((T - (T_TITLE - 0.4)) / 0.4)   # 最後は舞台へ溶ける
            if fade:
                frame = Image.blend(frame, sc.bg, fade)
            return frame
        if T < self.t_main:                               # 袖から登場（ボケが先に、奥の立ち位置まで歩く）
            t = T - T_TITLE
            ub, ut = clamp01(t / 2.8), clamp01((t - 0.25) / 2.75)
            frame = sc.bg.copy()
            sc.walkers(frame, WING_X + (xb - WING_X) * ease_out(ub), WING_X + 150 + (xt - WING_X - 150) * ease_out(ut),
                       t * 9, t * 9 + 1.5, ub < 1, ut < 1)
            return frame
        if T < self.t_out:                                # 漫才
            return sc.main_frame(T - self.t_main, n)
        if T < self.t_end:                                # 袖へ退場（ツッコミが先に）
            t = T - self.t_out
            ut, ub = clamp01(t / 2.2), clamp01((t - 0.4) / 2.4)
            frame = sc.bg.copy()
            sc.walkers(frame, xb + (WING_X - xb) * ease_in_out(ub), xt + (WING_X + 150 - xt) * ease_in_out(ut),
                       t * 9, t * 9 + 1.5, 0 < ub < 1, 0 < ut < 1)
            return frame
        return self.ending(T - self.t_end, n)

    def ending(self, t, n):
        """名場面を流しながら、2 人の声でチャンネル登録を頼む。"""
        sc = self.sc
        frame = self.end_bg.copy()
        # 名場面（叩くツッコミの前後を順に、くり返し）
        lens = [b - a for a, b in self.clips]
        u = t % sum(lens)
        for (a, b), ln in zip(self.clips, lens):
            if u < ln:
                shot = sc.main_frame(a + u, n).convert("RGB").resize((1056, 594), Image.BILINEAR)
                break
            u -= ln
        box = Image.new("RGBA", (1056 + 20, 594 + 20), (255, 255, 255, 255))
        box.paste(shot, (10, 10))
        box = box.rotate(-1.5, resample=Image.BICUBIC, expand=True)
        frame.alpha_composite(box, (int(W / 2 - box.width / 2), 40))
        frame.alpha_composite(self.label, (int(W / 2 - 528 - 20), 26))
        # チャンネル登録のボタン（どくんと脈打つ）
        s = 1 + 0.05 * max(0.0, math.sin(t * 5))
        center_paste(frame, scaled(self.sub_btn, s), W / 2, 760)
        center_paste(frame, self.sub_note, W / 2, 850)
        # 2 人（左右の下から顔を出して、話す人だけ口を動かす）
        te = t - 0.5
        k = max(0, min(int(te * self.end_tl["fps"]), len(self.end_mouth["A"]) - 1))
        ma = "open" if te >= 0 and self.end_mouth["A"][k] else "closed"
        mb = "open" if te >= 0 and self.end_mouth["B"][k] else "closed"
        for x, name, ph in ((260, f"boke_stand_{ma}", 0.0), (1660, f"tsukkomi_stand_{mb}", 1.3)):
            im = self.end_chars[name]
            frame.alpha_composite(im, (int(x - im.width / 2), int(H - im.height * 0.83 + 3 * math.sin(t * 2 + ph))))
        # 字幕（いま話しているセリフ）
        for a, b, who, text in self.captions:
            if a <= te < b + 0.2:
                if text not in self._cap_cache:
                    color = (255, 236, 150, 255) if who == "A" else (255, 255, 255, 255)
                    self._cap_cache[text] = caption_img(text, 46, color, 1100)
                center_paste(frame, self._cap_cache[text], W / 2, 985)
                break
        return frame


def build_audio(fmt, rate):
    """全体の音：出囃子・拍手・漫才（叩くツッコミの効果音つき）・エンディングの声と小さな曲。"""
    sc = fmt.sc
    n = int(fmt.total * rate) + rate
    mix = np.zeros(n, dtype=np.float32)

    def put(x, at, gain=1.0):
        i = int(at * rate)
        x = x[:max(0, n - i)]
        mix[i:i + len(x)] += x * gain

    def load(name):
        x, r = read_wav(ROOT / "assets" / "audio" / f"{name}.wav")
        return resample(x, r, rate)
    deb, clap = load("debayashi"), load("applause")
    sfx = {name: load(name) for name in ("slap", "pashi")}
    voice, vr = read_wav(sc.base / sc.tl["audio"])
    voice = resample(voice, vr, rate)
    put(deb, 0, 0.55)
    put(clap, T_TITLE, 0.45)
    put(voice, fmt.t_main)
    for h, lv in zip(sc.tl["hits"], sc.levels):
        name, gain = LEVELS[lv]["sfx"]
        put(sfx[name], fmt.t_main + h - 0.03, gain)
    # 締めの「どうも、ありがとうございましたー！」（最後の 2 人のセリフ）から、控えめな拍手を退場まで
    thanks = [ln["start"] for ln in sc.tl["lines"] if ln["who"] == "AB"]
    if thanks:
        put(clap, fmt.t_main + thanks[-1] + 0.3, APPLAUSE_GAIN)
    out = deb[:int((T_OUT + 0.6) * rate)].copy()
    out *= np.minimum(1, (len(out) - np.arange(len(out))) / (0.6 * rate))
    put(out, fmt.t_out, 0.5)
    end_voice, er = read_wav(ROOT / "build" / f"ending_{sc.combo}" / fmt.end_tl["audio"])
    put(resample(end_voice, er, rate), fmt.t_end + 0.5)
    loop_len = fmt.total - fmt.t_end
    loop = np.tile(deb, int(loop_len * rate / len(deb)) + 2)[:int(loop_len * rate)]
    loop *= np.minimum(1, (len(loop) - np.arange(len(loop))) / (1.0 * rate)) * np.minimum(1, np.arange(len(loop)) / (0.5 * rate))
    put(loop, fmt.t_end, 0.1)
    return np.clip(mix[:int(fmt.total * rate)], -1, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=None)
    ap.add_argument("--main-only", action="store_true")
    ap.add_argument("--frames", help="動画にせず、この秒（カンマ区切り）のコマを静止画で書き出す")
    ap.add_argument("--backend", choices=["chirp", "voicevox"])
    args = ap.parse_args()

    sc = Scene(args.script, args.backend)
    if args.frames:   # 静止画だけ（音も動画も作らない）
        draw = sc.main_frame if args.main_only else Format(sc).frame
        out = ROOT / "build" / "anim" / "frames"
        out.mkdir(parents=True, exist_ok=True)
        for i, t in enumerate(float(x) for x in args.frames.split(",")):
            png = out / f"{args.script}{'_main' if args.main_only else ''}_{t:g}.png"
            draw(t, i).convert("RGB").save(png)
            print(png)
        return
    fps = sc.fps
    out_dir = ROOT / "build" / "anim"
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.main_only:
        voice, rate = read_wav(sc.base / sc.tl["audio"])
        mix = voice.copy()
        for h, lv in zip(sc.tl["hits"], sc.levels):
            name, gain = LEVELS[lv]["sfx"]
            x, srate = read_wav(ROOT / "assets" / "audio" / f"{name}.wav")
            x = resample(x, srate, rate) * gain
            i = int((h - 0.03) * rate)
            mix[i:i + len(x)] += x[:len(mix) - i]
        total, draw = sc.tl["duration"], sc.main_frame
        stem = f"{args.script}_main"
    else:
        fmt = Format(sc)
        rate = 24000
        mix, total, draw = build_audio(fmt, rate), fmt.total, fmt.frame
        stem = args.script
    t_from, t_to = args.t_from, min(args.t_to or total, total)
    if (t_from, args.t_to) != (0.0, None):
        stem += f"_{t_from:g}-{t_to:g}"
    clip = np.clip(mix[int(t_from * rate):int(t_to * rate)], -1, 1)
    wav = out_dir / f"{stem}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((clip * 32767).astype("<i2").tobytes())

    mp4 = out_dir / f"{stem}.mp4"
    enc = subprocess.Popen([synth.ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(wav),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                            "-af", "alimiter=limit=0.89:level=disabled",   # 声・効果音・拍手が重なっても割れないよう -1dB で抑える
                            "-c:a", "aac", "-b:a", "192k", str(mp4)], stdin=subprocess.PIPE)
    for f in range(int((t_to - t_from) * fps)):
        t = t_from + f / fps
        enc.stdin.write(draw(t, f).convert("RGB").tobytes())
        if f % (fps * 10) == 0:
            print(f"  {t:6.1f} 秒")
    enc.stdin.close()
    enc.wait()
    wav.unlink()
    print(mp4, f"{t_to - t_from:.1f} 秒")


if __name__ == "__main__":
    main()
