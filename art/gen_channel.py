"""チャンネル「ほのぼの漫才劇場」のアイコンとバナーを作る。

    python art/gen_channel.py

できるもの：assets/channel/icon.png（800x800。YouTube では丸く切り抜かれるので、大事なものは真ん中の円に）
          assets/channel/banner.png（2560x1440。どの端末でも見えるのは真ん中の 1546x423。字と人物はそこに入れる）
先に art/gen_chars.py で部品（build/art/sprites/）を作っておく。
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import gen_chars as gc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "proto"))
from render import pill, text_img  # noqa: E402

OUT = ROOT / "assets" / "channel"
NAME = "ほのぼの漫才劇場"
SUB = "気になる話題を、ゆるっと漫才に"
DARK = (42, 34, 48, 255)


def banner():
    """舞台を少し上にずらして床を見せ、真ん中に名前、左右に 2 組のコンビ。"""
    bw, bh = 2560, 1440
    s = 0.38
    people = (gc.place(gc.male_boke("closed"), 455, 700, s) + gc.place(gc.male_tsukkomi("open", "stand"), 605, 700, s)
              + gc.place(gc.female_boke("closed"), 1315, 700, s) + gc.place(gc.female_tsukkomi("open", "stand"), 1465, 700, s))
    # 舞台を上にずらしたぶん、下に空いたところは舞台の手前の色で埋める
    body = (f'<g transform="translate(0 -110)">{gc.stage()}</g>'
            f'<rect x="0" y="895" width="1920" height="185" fill="#24130d"/><rect x="0" y="894" width="1920" height="8" fill="#e3b341"/>{people}')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{bw}" height="{bh}" viewBox="0 0 1920 1080">{body}</svg>'
    path = OUT / "banner_base.svg"
    path.write_text(svg, encoding="utf-8")
    base = Image.open(gc.to_png(path, bw, bh)).convert("RGBA")
    path.unlink()
    path.with_suffix(".png").unlink()
    title = text_img(NAME, 150, (255, 236, 150, 255), DARK, 16, max_w=900)
    base.alpha_composite(title, ((bw - title.width) // 2, 540))
    sub = pill(SUB, 46, (255, 255, 255, 235), DARK, pad=(30, 10))
    base.alpha_composite(sub, ((bw - sub.width) // 2, 540 + title.height + 24))
    base.convert("RGB").save(OUT / "banner.png")
    return OUT / "banner.png"


def icon():
    """4 人の顔を 2x2 に並べ、真ん中にセンターマイク。背景は舞台の放射の光。"""
    size = 800
    sp = ROOT / "build" / "art" / "sprites"
    bg = Image.open(sp / "male" / "bg.png").convert("RGBA").crop((560, 60, 1360, 860)).resize((size, size))
    bg = Image.alpha_composite(bg, Image.new("RGBA", (size, size), (255, 200, 120, 40)))
    # (部品, 顔の真ん中の y, 切り出す大きさ, 置く真ん中)
    heads = [("male/boke_stand_open", 960 - 690, 420, (245, 255)), ("male/tsukkomi_stand_open", 960 - 640, 330, (555, 255)),
             ("female/boke_stand_closed", 960 - 470, 230, (245, 555)), ("female/tsukkomi_stand_open", 960 - 560, 280, (555, 555))]
    out = bg.copy()
    for name, cy, box, (px, py) in heads:
        im = Image.open(sp / f"{name}.png").convert("RGBA").crop((500 - box // 2, cy - box // 2, 500 + box // 2, cy + box // 2))
        im = im.resize((330, 330), Image.LANCZOS)
        shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
        shadow.putalpha(im.getchannel("A").point(lambda a: int(a * 0.35)))
        out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)), (px - 165 + 6, py - 165 + 8))
        out.alpha_composite(im, (px - 165, py - 165))
    # 丸く切り抜いたときの縁（金色の輪）
    d = ImageDraw.Draw(out)
    d.ellipse((14, 14, size - 14, size - 14), outline=(227, 179, 65, 255), width=14)
    out.convert("RGB").save(OUT / "icon.png")
    return OUT / "icon.png"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print(banner())
    print(icon())
