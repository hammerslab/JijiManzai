"""サムネイル 3 案（1280x720）を作る。YouTube Studio の「テストと比較」にかける。

    python proto/thumbnail.py dopagaki maratan

できるもの：build/<台本>/thumbnail_1〜3.png
  1：いちばん強いツッコミの瞬間を寄りで
  2：2 人の顔を大きく
  3：見つめ合う場面（なければ 2 番目に強いツッコミ）を寄りで
文句は台本の頭の「thumb: 文句1／文句2／文句3」（｜で改行）。なければ題名。
どれにも【ほのぼの漫才】の札と「お題：〇〇」を付ける。動画は作らない（声とタイムラインは先に synth.py で作っておく）。
"""
import sys

from PIL import Image, ImageDraw, ImageFilter

import render
from render import FEET, FLOOR_Y, ROOT, Scene, pill, text_img

TW, TH = 1280, 720
THUMB_FONT = "C:/Windows/Fonts/BIZ-UDGothicB.ttc"
# 顔の真ん中（部品画像の中。足元 (500, 960) から上へ）
FACE = {"male": {"A": -655, "B": -615}, "female": {"A": -450, "B": -546},
        "xmas": {"A": -491, "B": -461, "C": -338, "D": -410}}   # 4 人の回は部品が 0.75 倍
SIZE = {"xmas": 0.75}   # 部品の大きさ（切り出す幅・顔の拡大をこれで割る）


def crop_zoom(frame, cx, cy, w):
    """(cx, cy) を真ん中に、横 w の 16:9 を切り出して 1280x720 にする。"""
    h = w * 9 / 16
    x0 = max(0, min(render.W - w, cx - w / 2))
    y0 = max(0, min(render.H - h, cy - h / 2))
    return frame.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((TW, TH), Image.LANCZOS)


def copy_img(text, size=118):
    """大きな文句（黄色・太い縁取り）。｜で改行。"""
    lines = [text_img(ln, size, (255, 226, 60, 255), (30, 20, 40, 255), 16, THUMB_FONT, max_w=TW - 80) for ln in text.split("｜")]
    out = Image.new("RGBA", (max(im.width for im in lines), sum(im.height for im in lines) + 4 * (len(lines) - 1)), (0, 0, 0, 0))
    y = 0
    for im in lines:
        out.alpha_composite(im, ((out.width - im.width) // 2, y))
        y += im.height + 4
    return out


def decorate(img, copy, theme, copy_y="bottom"):
    img = img.convert("RGBA")
    shade = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for i in range(260):   # 文句の後ろを少し暗くする
        a = int(170 * (i / 260) ** 1.5)
        y = TH - 260 + i if copy_y == "bottom" else 260 - i
        d.line([(0, y), (TW, y)], fill=(10, 5, 20, a))
    img.alpha_composite(shade)
    c = copy_img(copy)
    y = TH - c.height - 28 if copy_y == "bottom" else 28 + 70
    img.alpha_composite(c, ((TW - c.width) // 2, y))
    badge = pill("ほのぼの漫才", 40, (230, 40, 60, 255), (255, 255, 255, 255), pad=(26, 10), font=THUMB_FONT)
    img.alpha_composite(badge, (24, 20))
    if theme:
        tp = pill(f"お題：{theme}", 32, (255, 214, 64, 255), (42, 34, 48, 255), pad=(22, 8), font=THUMB_FONT)
        img.alpha_composite(tp, (TW - tp.width - 24, 24))
    return img.convert("RGB")


def faces(sc):
    """顔を大きく：ぼかした舞台に、ボケ（正面・口を開け）とツッコミ（口を開け）を並べる。4 人の回は 4 人を少し小さめに。"""
    bg = sc.bg.filter(ImageFilter.GaussianBlur(8)).resize((TW, TH))
    out = bg.convert("RGBA")
    many = len(sc.cast) > 2
    xs = (330, 950) if not many else [TW * (i + 0.5) / len(sc.cast) for i in range(len(sc.cast))]
    for m, cx in zip(sc.cast, xs):
        sp = sc.S[f"{m['sp']}_stand_open"]
        fy = FEET[1] + FACE[sc.combo][m["who"]]
        s = (1.45 if many else 1.9) / SIZE.get(sc.combo, 1.0)
        big = sp.resize((int(sp.width * s), int(sp.height * s)), Image.LANCZOS)
        out.alpha_composite(big, (int(cx - FEET[0] * s), int((240 if many else 300) - fy * s)))   # 4 人は文句にかからないよう少し上に
    return out


def main():
    for name in sys.argv[1:]:
        sc = Scene(name)
        tl = sc.tl
        copies = (tl.get("thumb") or [])[:3]
        copies += [tl.get("title", name)] * (3 - len(copies))
        k = SIZE.get(sc.combo, 1.0)
        kind = {m["who"]: m["kind"] for m in sc.cast}
        # 女のボケは「いちばん強い」だと回っていて顔が見えないので、強い（2）までから選ぶ
        def top(i):
            return 2 if kind[render.PARTNER[sc.hit_who[i]]] == "female" else 3
        order = sorted(range(len(tl["hits"])), key=lambda i: (sc.levels[i] if sc.levels[i] <= top(i) else 0, i), reverse=True)
        strongest = tl["hits"][order[0]] if order else tl["duration"] / 2
        second = tl["hits"][order[1]] if len(order) > 1 else strongest
        # 1 枚目は叩いた組に寄る（2 人の回は 2 人の真ん中）
        hitter = sc.hit_who[order[0]] if order else "B"
        victim = render.PARTNER[hitter]
        mid = (sc.xs[hitter] + sc.xs[victim]) / 2
        female = kind[victim] == "female"
        face_y = FLOOR_Y + FACE[sc.combo][victim] + 120 * k

        shots = []
        f1 = sc.main_frame(strongest + 0.12, 1, bubbles=False)
        shots.append(decorate(crop_zoom(f1, mid - 40 * k, face_y + (-40 if female else 60) * k, 1250 * k), copies[0], tl.get("theme")))
        shots.append(decorate(faces(sc), copies[1], tl.get("theme")))
        t3 = tl["looks"][0][0] + 0.6 if tl["looks"] else second + 0.12
        f3 = sc.main_frame(t3, 1, bubbles=False)
        if len(sc.cast) > 2:   # 4 人の回の 3 枚目は 4 人そろって
            shots.append(decorate(crop_zoom(f3, sum(sc.xs.values()) / 4, 600, 1400), copies[2], tl.get("theme")))
        else:
            mid2 = sum(sc.c["x"]) / 2
            face2 = FLOOR_Y + FACE[sc.combo]["A"] + 120
            shots.append(decorate(crop_zoom(f3, mid2, face2 - (90 if sc.combo == "female" else 0), 1000), copies[2], tl.get("theme")))
        for i, im in enumerate(shots, 1):
            out = sc.base / f"thumbnail_{i}.png"
            im.save(out)
            print(out)


if __name__ == "__main__":
    main()
