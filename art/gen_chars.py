"""舞台とコンビ 4 人の絵（SVG）を作り、PNG に書き出す試作。ドット絵ではなく、輪郭線つきのフラットな 2D。

    python art/gen_chars.py

できるもの：build/art/*.svg と *.png
  stage            舞台だけ（センターマイクなし）
  combo_male       男性コンビ（ボケ＝痩せたアフロ、ツッコミ＝太ったモヒカン）
  combo_female     女性コンビ（ボケ＝小さく痩せたボブ、ツッコミ＝小太りの金髪ギャル）
  sheet            4 人の口を閉じた顔・開けた顔

キャラは足元の中央を (0, 0) にして、上を y のマイナスで描く。口（mouth）と腕（pose）を差し替えられるようにしておく
（あとで Godot で口パク・ツッコミの動きを付けるため）。
"""
import glob
import math
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "art"
W, H = 1920, 1080
FLOOR_Y = 930          # キャラの足元
OL = "#2a2230"         # 輪郭線
LW = 5                 # 輪郭線の太さ

SKIN = "#f7d5bc"
SKIN_TAN = "#e9b48a"
CHEEK = "#ff8a9a"
SANTA_RED, SANTA_RED_D, FUR = "#d8343f", "#a8222c", "#fbf7f2"   # クリスマスの回のサンタの衣装


# ---------- 部品 ----------

def st(fill, w=LW, extra=""):
    return f'fill="{fill}" stroke="{OL}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" {extra}'


def ellipse(cx, cy, rx, ry, fill, w=LW, extra=""):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" {st(fill, w, extra)}/>'


def circle(cx, cy, r, fill, w=LW, extra=""):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" {st(fill, w, extra)}/>'


def path(d, fill, w=LW, extra=""):
    return f'<path d="{d}" {st(fill, w, extra)}/>'


def line(d, w=4, color=OL):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def rrect(x, y, w, h, r, fill, lw=LW):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" {st(fill, lw)}/>'


def limb(pts, width, color):
    """腕や脚。輪郭の太い線の上に、色の線を重ねる。"""
    d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
    common = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<path d="{d}" {common} stroke="{OL}" stroke-width="{width + 2 * LW}"/>'
            f'<path d="{d}" {common} stroke="{color}" stroke-width="{width}"/>')


def bumpy(circles, fill):
    """円を寄せ集めた、もこもこの形（アフロ）。外側だけに輪郭線が出るよう、輪郭の円を先に全部描く。"""
    out = "".join(f'<circle cx="{x}" cy="{y}" r="{r + LW}" fill="{OL}"/>' for x, y, r in circles)
    return out + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>' for x, y, r in circles)


def chop_hand(x, y, skin, angle=-8):
    """ツッコミの手（手刀を横から見た形）。"""
    return (f'<g transform="translate({x} {y}) rotate({angle})">'
            + ellipse(0, 0, 17, 30, skin) + line("M -6 -18 L -6 14", 3, "#c99a7e") + "</g>")


def santa_hat(cx, base_y, hw, h, tilt=-10):
    """サンタの帽子。base_y は白いふちの真ん中、hw はふちの幅の半分、h は高さ。先は右へ垂れて、白い玉が付く。"""
    tip = (cx + hw * 1.15, base_y - h * 0.5)
    d = (f"M {cx - hw} {base_y} Q {cx - hw * 0.5} {base_y - h * 1.05} {cx + hw * 0.35} {base_y - h} "
         f"Q {cx + hw * 1.05} {base_y - h * 0.95} {tip[0]} {tip[1]} "
         f"Q {cx + hw * 0.75} {base_y - h * 0.6} {cx + hw * 0.6} {base_y - h * 0.45} "
         f"Q {cx + hw * 0.85} {base_y - h * 0.2} {cx + hw} {base_y} Z")
    out = path(d, SANTA_RED) + line(f"M {cx - hw * 0.3} {base_y - h * 0.55} Q {cx} {base_y - h * 0.85} {cx + hw * 0.4} {base_y - h * 0.9}", 3, SANTA_RED_D)
    out += rrect(cx - hw - 12, base_y - 22, 2 * hw + 24, 44, 22, FUR)
    out += circle(tip[0], tip[1] + 6, hw * 0.24, FUR)
    return f'<g transform="rotate({tilt} {cx} {base_y})">{out}</g>'


def fur_band(x0, x1, y, hgt=22):
    """服のすそ・ふちの白いふわふわ。"""
    return rrect(x0, y - hgt / 2, x1 - x0, hgt, hgt / 2, FUR, 4)


def sleepy_eyes(cx, cy, dx, size=1.0, look=0):
    """ボケの目：小さな黒目に、重たいまぶたの線。淡々とした顔。"""
    out = ""
    for s in (-1, 1):
        x = cx + s * dx
        out += f'<ellipse cx="{x + look}" cy="{cy}" rx="{5 * size}" ry="{6 * size}" fill="{OL}"/>'
        out += line(f"M {x - 13 * size} {cy - 6 * size} Q {x} {cy - 12 * size} {x + 13 * size} {cy - 6 * size}", 4)
    return out


def shout_mouth(cx, cy, wdt, hgt, inside="#7a2230", lip=None):
    """大きく開けた口（ツッコミ）。上の歯と舌つき。"""
    d = (f"M {cx - wdt} {cy} Q {cx} {cy + 4} {cx + wdt} {cy} "
         f"Q {cx + wdt * 0.8} {cy + hgt} {cx} {cy + hgt} Q {cx - wdt * 0.8} {cy + hgt} {cx - wdt} {cy} Z")
    out = path(d, inside, 4 if lip is None else 5, "" if lip is None else f'stroke="{lip}"')
    out = out.replace(f'stroke="{OL}" stroke-width', 'stroke-width') if lip else out
    out += f'<path d="M {cx - wdt * 0.8} {cy + 2} L {cx + wdt * 0.8} {cy + 2} L {cx + wdt * 0.7} {cy + 9} L {cx - wdt * 0.7} {cy + 9} Z" fill="#fff"/>'
    out += f'<ellipse cx="{cx}" cy="{cy + hgt * 0.72}" rx="{wdt * 0.45}" ry="{hgt * 0.2}" fill="#e46f7c"/>'
    return out


# ---------- キャラクター ----------

def montsuki(w_top, y_top, y_v, crest_y, crest_dx, himo_y):
    """紋付の胸元：白い半衿の V、家紋（白い丸）、白い羽織紐。"""
    out = line(f"M {-w_top} {y_top} L 0 {y_v}", 9, "#ffffff") + line(f"M {w_top} {y_top} L 0 {y_v}", 9, "#ffffff")
    for s in (-1, 1):
        out += circle(s * crest_dx, crest_y, 10, "#ffffff", 3) + circle(s * crest_dx, crest_y, 4, "#2b2a33", 0)
    out += circle(-8, himo_y, 9, "#ffffff", 3) + circle(8, himo_y, 9, "#ffffff", 3) + line(f"M 0 {himo_y + 6} L 0 {himo_y + 30}", 5, "#ffffff")
    return out


def hakama(x_top, y_top, x_bot, color="#6b6f7a"):
    """袴（縦じま。真ん中で二つに分かれる）。"""
    out = path(f"M {-x_top} {y_top} L {x_top} {y_top} L {x_bot} -14 L 8 -14 L 0 {y_top + 150} L -8 -14 L {-x_bot} -14 Z", color)
    for i in range(1, 4):
        x = x_top * i / 4
        out += line(f"M {x} {y_top + 6} L {x_bot * i / 4 + 6} -20", 3, "#555864") + line(f"M {-x} {y_top + 6} L {-x_bot * i / 4 - 6} -20", 3, "#555864")
    return out


def male_boke(mouth="closed", pose="stand", look=False, costume=None):
    """痩せたアフロ（ボケ）。ひょろ長い体、細いスーツ、眠そうな目。
    pose="hit"（ツッコまれた）は、腰から上が「く」の字に折れ曲がり、腕が泳ぐ。叩く強さで折れる角度を変える：
    hit1＝25°（ふつう）、hit＝42°（強い）、hit3＝60°（いちばん強い）。
    costume="santa" はクリスマスの回の衣装（赤いスーツに白いすそ、緑のネクタイ、アフロの上にサンタの帽子）、
    "wafuku" はお正月の回の衣装（黒の紋付の羽織にしま模様の袴、白い足袋に草履）。"""
    santa, wafuku = costume == "santa", costume == "wafuku"
    bend = {"hit1": 25, "hit": 42, "hit3": 60}.get(pose)
    pose = "hit" if bend else pose
    suit, suit_d = (SANTA_RED, SANTA_RED_D) if santa else ("#2b2a33", "#2b2a33") if wafuku else ("#4f9d8f", "#3d8174")
    if wafuku:   # 草履と足袋、袴
        low = [ellipse(-26, -8, 30, 10, "#c8a46a"), ellipse(26, -8, 30, 10, "#c8a46a"), ellipse(-24, -18, 20, 12, "#f4f1ea", 3), ellipse(24, -18, 20, 12, "#f4f1ea", 3)]
        low.append(hakama(56, -330, 70))
    else:
        low = [ellipse(-26, -8, 30, 12, "#5a3a2a"), ellipse(26, -8, 30, 12, "#5a3a2a")]
        low.append(rrect(-44, -335, 32, 325, 12, suit_d))
        low.append(rrect(12, -335, 32, 325, 12, suit_d))
    g = []
    g.append(path("M -40 -572 Q -68 -568 -66 -540 L -56 -318 Q 0 -306 56 -318 L 66 -540 Q 68 -568 40 -572 Z", suit))
    if wafuku:
        g.append(path("M -22 -572 L 22 -572 L 0 -498 Z", "#8a8f99", 4))
        g.append(montsuki(24, -572, -500, -530, 40, -470))
    else:
        g.append(path("M -22 -572 L 22 -572 L 0 -498 Z", "#ffffff", 4))
        g.append(path("M -6 -562 L 6 -562 L 9 -430 L 0 -416 L -9 -430 Z", "#2f8f4e" if santa else "#9b2335", 3))
        g.append(line("M -26 -572 L -4 -470", 4) + line("M 26 -572 L 4 -470", 4))
        g.append(circle(0, -392, 5, "#7a1820" if santa else "#2f6b60", 3))
    if santa:
        g.append(fur_band(-60, 60, -318, 24))
    if pose == "hit":
        arms = [[(-64, -552), (-124, -612), (-150, -694)], [(64, -552), (124, -588), (172, -560)]]
    else:
        arms = [[(s * 64, -552), (s * 80, -450), (s * 78, -352)] for s in (-1, 1)]
    for pts in arms:
        g.append(limb(pts, 24, suit))
        g.append(circle(pts[-1][0], pts[-1][1] + (10 if pose != "hit" else 0), 15, SKIN))
    g.append(rrect(-14, -618, 28, 54, 8, SKIN))
    # アフロ（後ろ）
    ring = [(round(115 * math.cos(math.radians(a))), round(-705 + 105 * math.sin(math.radians(a))), 44)
            for a in range(0, 360, 26)]
    g.append(bumpy(ring + [(0, -705, 112)], "#3a2a22"))
    g.append(ellipse(-50, -650, 10, 15, SKIN) + ellipse(50, -650, 10, 15, SKIN))
    g.append(ellipse(0, -652, 48, 64, SKIN))
    # 生え際（前のもこもこ）
    bumps = " ".join(f"Q {x - 11} -676 {x - 22} -692" for x in range(44, -44, -22))
    g.append(f'<path d="M -46 -745 L 46 -745 L 44 -692 {bumps} Z" fill="#3a2a22"/>')
    g.append(line(f"M 44 -692 {bumps}", LW))
    if santa:   # アフロのてっぺんに、ちょこんと
        g.append(santa_hat(0, -790, 80, 150, -8))
    g.append(sleepy_eyes(0, -655, 19, look=6 if look else 0))
    g.append(line("M -31 -674 L -9 -674", 4) + line("M 31 -674 L 9 -674", 4))
    g.append(line("M 1 -648 Q 8 -630 -2 -626", 3))
    if mouth == "open":
        g.append(ellipse(0, -606, 10, 8, "#7a2230", 4))
    else:
        g.append(line("M -11 -607 L 11 -607", 4))
    upper = "".join(g)
    if pose == "hit":
        upper = f'<g transform="rotate({-bend} 0 -322)">{upper}</g>'
    return "".join(low) + upper


def male_tsukkomi(mouth="open", pose="tsukkomi", look=False, costume=None):
    """太ったモヒカン（ツッコミ）。丸い体、紺のスーツに赤い蝶ネクタイ、ぱっちりした目。
    costume="santa" は赤い服に黒いベルト、緑の蝶ネクタイ、サンタの帽子（モヒカンが突き抜ける）、
    "wafuku" は深緑の紋付の羽織にしま模様の袴、白い足袋に草履。"""
    santa, wafuku = costume == "santa", costume == "wafuku"
    suit, suit_d = (SANTA_RED, SANTA_RED_D) if santa else ("#2f5e4a", "#2f5e4a") if wafuku else ("#3b4f86", "#2f3e66")
    tie = "#2f8f4e" if santa else "#d6283c"
    if wafuku:
        g = [ellipse(-46, -8, 42, 11, "#c8a46a"), ellipse(46, -8, 42, 11, "#c8a46a"), ellipse(-44, -20, 30, 13, "#f4f1ea", 3), ellipse(44, -20, 30, 13, "#f4f1ea", 3)]
        g.append(hakama(108, -260, 128))
    else:
        g = [ellipse(-46, -10, 42, 15, "#26262c"), ellipse(46, -10, 42, 15, "#26262c")]
        g.append(rrect(-84, -240, 66, 228, 22, suit_d))
        g.append(rrect(18, -240, 66, 228, 22, suit_d))
    if pose == "tsukkomi":
        far = limb([(130, -480), (182, -405), (136, -352)], 50, suit) + circle(130, -350, 24, SKIN)
    else:
        far = limb([(132, -480), (165, -380), (156, -292)], 50, suit) + circle(156, -282, 25, SKIN)
    g.append(far)
    g.append(ellipse(0, -385, 150, 172, suit))
    if wafuku:
        g.append(path("M -48 -548 L 48 -548 L 0 -430 Z", "#8a8f99", 4))
        g.append(montsuki(50, -548, -430, -490, 92, -400))
    else:
        g.append(path("M -48 -548 L 48 -548 L 0 -392 Z", "#ffffff", 4))
        g.append(line("M -52 -548 L -6 -400", 4) + line("M 52 -548 L 6 -400", 4))
    if santa:   # サンタの黒いベルトと金のバックル、すその白いふわふわ
        g.append(rrect(-142, -350, 284, 38, 8, "#26262c", 4))
        g.append(rrect(-26, -356, 52, 50, 8, "#e3b341", 4) + rrect(-12, -342, 24, 22, 4, "#26262c", 3))
        g.append(fur_band(-118, 118, -222, 26))
    elif not wafuku:
        g.append(circle(0, -360, 6, "#26314f", 3) + circle(0, -300, 6, "#26314f", 3))
    if not wafuku:
        g.append(path("M 0 -532 L -30 -548 L -30 -514 Z", tie, 4) + path("M 0 -532 L 30 -548 L 30 -514 Z", tie, 4)
                 + circle(0, -532, 8, tie, 4))
    if pose == "tsukkomi":
        g.append(limb([(-128, -488), (-222, -452), (-300, -468)], 50, suit))
        g.append(chop_hand(-320, -468, SKIN))
    else:
        g.append(limb([(-132, -480), (-165, -380), (-156, -292)], 50, suit))
        g.append(circle(-156, -282, 25, SKIN))
    # 頭
    g.append(circle(-84, -612, 17, SKIN) + circle(84, -612, 17, SKIN))
    g.append(circle(0, -615, 86, SKIN))
    g.append('<path d="M -84 -628 A 86 86 0 0 1 84 -628 Q 0 -668 -84 -628 Z" fill="#9c8478" opacity="0.35"/>')
    g.append(line("M -46 -545 Q 0 -522 46 -545", 4))
    if santa:   # 帽子を先にかぶせて、モヒカンを上から突き抜けさせる
        g.append(santa_hat(-4, -668, 84, 130, -6))
    g.append(path("M -22 -697 L -32 -748 L -12 -734 L -16 -792 L 4 -760 L 6 -810 L 22 -764 L 36 -792 L 30 -736 L 44 -744 L 24 -697 Z",
                  "#e0405a"))
    g.append(line("M -54 -652 L -14 -638", 10) + line("M 54 -652 L 14 -638", 10))
    for s in (-1, 1):
        g.append(circle(s * 31, -618, 14, "#ffffff", 4) + f'<circle cx="{s * 28 - (7 if look else 0)}" cy="{-616}" r="7" fill="{OL}"/>')
    g.append(ellipse(0, -594, 10, 8, "#eab89c", 3))
    g.append(f'<ellipse cx="-52" cy="-584" rx="13" ry="7" fill="{CHEEK}" opacity="0.5"/>'
             f'<ellipse cx="52" cy="-584" rx="13" ry="7" fill="{CHEEK}" opacity="0.5"/>')
    if mouth == "open":
        g.append(shout_mouth(0, -574, 28, 40))
    else:
        g.append(line("M -20 -566 Q 0 -558 20 -566", 5))
    return "".join(g)


def flowers(pts, r, fill, center="#e3b341"):
    """着物の柄・髪飾りの花（5 枚の花びら）。"""
    out = ""
    for x, y in pts:
        for a in range(0, 360, 72):
            out += f'<circle cx="{x + r * 0.6 * math.cos(math.radians(a - 90)):.1f}" cy="{y + r * 0.6 * math.sin(math.radians(a - 90)):.1f}" r="{r * 0.5:.1f}" fill="{fill}"/>'
        out += f'<circle cx="{x}" cy="{y}" r="{r * 0.28:.1f}" fill="{center}"/>'
    return out


def female_boke(mouth="closed", pose="stand", look=False, costume=None):
    """小さく痩せたボブ（ボケ）。ぱっつん前髪、淡い水色のワンピース、眠そうな目。
    pose="hit"（ツッコまれた）は、両手を上げ、脚を開いて飛ばされる形。傾きと移動は動画の側で付ける（叩く強さで変える）。
    costume="santa" は赤いワンピースに白いすそ、サンタの帽子。"wafuku" は朱色の振袖（梅の柄、金の帯、長い袖）に花の髪飾り。"""
    santa, wafuku = costume == "santa", costume == "wafuku"
    pose = "hit" if pose.startswith("hit") else pose
    dress = SANTA_RED if santa else "#d8454a" if wafuku else "#9fb7e0"
    hair = "#2a2633"
    leg = "#f4f1ea" if wafuku else "#4a4458"   # 振袖のときは白い足袋
    if pose == "hit":
        g = [limb([(-14, -196), (-40, -20)], 16, leg), limb([(14, -196), (44, -30)], 16, leg),
             ellipse(-44, -14, 19, 10, "#c0392b"), ellipse(50, -24, 19, 10, "#c0392b")]
    else:
        g = [ellipse(-17, -8, 19, 10, "#c0392b"), ellipse(17, -8, 19, 10, "#c0392b")]
        g.append(rrect(-25, -200, 16, 192, 8, leg))
        g.append(rrect(9, -200, 16, 192, 8, leg))
    if wafuku:   # 振袖は足首まで（飛ばされたときは膝まで）。長い袖を先に描く
        if pose != "hit":
            for s in (-1, 1):
                g.append(path(f"M {s * 46} -372 L {s * 84} -330 L {s * 86} -196 Q {s * 70} -180 {s * 54} -196 L {s * 50} -300 Z", dress))
                g.append(flowers([(s * 70, -240)], 12, "#ffd6e0"))
        hem = -150 if pose == "hit" else -26
        g.append(path(f"M -32 -392 Q -46 -388 -46 -362 L -60 {hem} Q 0 {hem + 10} 60 {hem} L 46 -362 Q 46 -388 32 -392 Z", dress))
        g.append(line(f"M -8 -380 L 10 {hem + 4}", 3, "#a8222c"))   # おくみの線
        g.append(flowers([(-26, -250), (24, -170), (-20, -90), (30, -60)][:4 if pose != "hit" else 2], 14, "#ffd6e0"))
        g.append(rrect(-48, -336, 96, 42, 6, "#e3b341") + line("M -46 -315 L 46 -315", 4, "#d8343f"))   # 金の帯と帯締め
    else:
        g.append(path("M -32 -392 Q -46 -388 -46 -362 L -64 -192 Q 0 -178 64 -192 L 46 -362 Q 46 -388 32 -392 Z", dress))
    if santa:
        g.append(fur_band(-70, 70, -188, 22))
    for s in (-1, 1):
        if pose == "hit":
            g.append(limb([(s * 44, -378), (s * 86, -430), (s * 100, -496)], 17, dress) + circle(s * 100, -504, 10, SKIN))
        else:
            g.append(limb([(s * 44, -378), (s * 60, -300), (s * 60, -240)], 17, dress) + circle(s * 60, -232, 10, SKIN))
    g.append(path("M -16 -392 L 0 -376 L -2 -362 L -24 -370 Z", "#ffffff", 3) + path("M 16 -392 L 0 -376 L 2 -362 L 24 -370 Z", "#ffffff", 3))
    g.append(rrect(-9, -416, 18, 30, 6, SKIN))
    # ボブ（後ろ）
    g.append(path("M -68 -452 Q -72 -540 0 -544 Q 72 -540 68 -452 L 70 -398 Q 36 -388 0 -390 Q -36 -388 -70 -398 Z", hair))
    g.append(ellipse(0, -450, 50, 54, SKIN))
    # 前髪（ぱっつん）と横の髪
    g.append(path("M -58 -420 Q -66 -528 0 -530 Q 66 -528 58 -420 L 48 -420 L 46 -472 L -46 -472 L -48 -420 Z", hair))
    if santa:
        g.append(santa_hat(0, -512, 66, 120, -10))
    if wafuku:   # 花の髪飾り
        g.append(flowers([(46, -500)], 26, "#ff8fab") + flowers([(30, -522)], 16, "#ffffff"))
    g.append(sleepy_eyes(0, -446, 17, 0.9, look=5 if look else 0))
    g.append(f'<ellipse cx="-31" cy="-428" rx="9" ry="5" fill="{CHEEK}" opacity="0.45"/>'
             f'<ellipse cx="31" cy="-428" rx="9" ry="5" fill="{CHEEK}" opacity="0.45"/>')
    if mouth == "open":
        g.append(ellipse(0, -416, 7, 6, "#7a2230", 3))
    else:
        g.append(line("M -6 -417 L 6 -417", 3.5))
    return "".join(g)


def female_tsukkomi(mouth="open", pose="tsukkomi", look=False, costume=None):
    """小太りの金髪ギャル（ツッコミ）。ピンクのオフショル、デニムのミニ、白の厚底、金のフープピアス。
    costume="santa" は赤いオフショルとミニに白いふち、サンタの帽子（ハートの髪留めは帽子の上に）。
    "wafuku" はギャルの振袖（紫に金の花、金の帯、白いふわふわのショール、大きな花の髪飾り。足元は白の厚底のまま）。"""
    santa, wafuku = costume == "santa", costume == "wafuku"
    skin = SKIN_TAN
    top = SANTA_RED if santa else "#7b3fa0" if wafuku else "#ff7eb6"
    arm = top if wafuku else skin   # 振袖は腕も袖の中
    blonde, blonde_d = "#f5d36b", "#e0b545"
    g = [rrect(-72, -64, 58, 62, 16, "#ffffff"), rrect(14, -64, 58, 62, 16, "#ffffff")]
    g.append(f'<rect x="-72" y="-18" width="58" height="16" rx="6" fill="#c9c9d6"/><rect x="14" y="-18" width="58" height="16" rx="6" fill="#c9c9d6"/>')
    g.append(rrect(-68, -228, 48, 170, 20, skin))
    g.append(rrect(20, -228, 48, 170, 20, skin))
    if pose == "tsukkomi":
        g.append(limb([(108, -445), (158, -372), (114, -318)], 42, arm))
    else:
        if wafuku:   # 長い袖
            g.append(path("M 110 -440 L 170 -380 L 172 -230 Q 150 -214 128 -230 L 124 -330 Z", top) + flowers([(150, -270)], 16, "#e3b341", "#ffffff"))
        g.append(limb([(108, -448), (140, -370), (134, -292)], 42, arm) + circle(134, -282, 20, skin))
    g.append(ellipse(0, -458, 90, 28, skin))
    if wafuku:   # 足首までの振袖、金の帯、白いショール
        g.append(path("M -106 -452 Q -150 -370 -118 -300 L -126 -66 Q 0 -54 126 -66 L 118 -300 Q 150 -370 106 -452 Q 0 -432 -106 -452 Z", top))
        g.append(flowers([(-70, -240), (60, -180), (-40, -110), (84, -100), (10, -300)], 18, "#e3b341", "#ffffff"))
        g.append(rrect(-124, -350, 248, 56, 8, "#e3b341") + line("M -122 -322 L 122 -322", 5, "#d8343f"))
        g.append(line("M -112 -452 Q 0 -420 112 -452", 52, OL) + line("M -112 -452 Q 0 -420 112 -452", 42, FUR))
    else:
        g.append(path("M -106 -452 Q -150 -370 -118 -300 L 118 -300 Q 150 -370 106 -452 Q 0 -432 -106 -452 Z", top))
    if santa:   # 胸元とすそに白いふわふわ
        g.append(line("M -104 -446 Q 0 -426 104 -446", 30, OL) + line("M -104 -446 Q 0 -426 104 -446", 20, FUR))
        g.append(path("M -118 -306 L 118 -306 L 136 -206 Q 0 -188 -136 -206 Z", SANTA_RED_D))
        g.append(line("M -134 -204 Q 0 -186 134 -204", 30, OL) + line("M -134 -204 Q 0 -186 134 -204", 20, FUR))
    elif not wafuku:
        g.append(line("M -100 -440 Q 0 -420 100 -440", 3, "#ffb3d4"))
        g.append(line("M -60 -330 Q 0 -312 60 -330", 3, "#e2609c"))
        g.append(path("M -118 -306 L 118 -306 L 136 -206 Q 0 -188 -136 -206 Z", "#6f8fc4"))
        g.append(line("M -66 -300 L -74 -210", 3, "#5a77a8") + line("M 66 -300 L 74 -210", 3, "#5a77a8"))
    if pose == "tsukkomi":
        g.append(limb([(-104, -446), (-192, -402), (-276, -360)], 42, arm))
        g.append(f'<ellipse cx="-262" cy="-366" rx="7" ry="20" fill="none" stroke="#e8b830" stroke-width="5" transform="rotate(-24 -262 -366)"/>')
        g.append(chop_hand(-294, -352, skin, -24))
    else:
        if wafuku:
            g.append(path("M -110 -440 L -170 -380 L -172 -230 Q -150 -214 -128 -230 L -124 -330 Z", top) + flowers([(-150, -270)], 16, "#e3b341", "#ffffff"))
        g.append(limb([(-108, -448), (-140, -370), (-134, -292)], 42, arm) + circle(-134, -282, 20, skin))
    # 髪（後ろ）
    g.append(path("M -80 -548 Q -90 -634 0 -636 Q 90 -634 80 -548 Q 98 -486 84 -432 Q 64 -416 54 -446 L -54 -446 Q -64 -416 -84 -432 Q -98 -486 -80 -548 Z", blonde))
    g.append(line("M -78 -520 Q -90 -480 -76 -444", 3, blonde_d) + line("M 78 -520 Q 90 -480 76 -444", 3, blonde_d))
    g.append(ellipse(0, -546, 78, 70, skin))
    # ピアス
    g.append(f'<circle cx="-72" cy="-500" r="14" fill="none" stroke="#e8b830" stroke-width="5"/>'
             f'<circle cx="72" cy="-500" r="14" fill="none" stroke="#e8b830" stroke-width="5"/>')
    # 前髪（流した前髪）
    g.append(path("M -74 -540 Q -80 -628 0 -624 Q 74 -620 76 -548 Q 46 -602 -6 -588 Q -42 -580 -74 -540 Z", blonde))
    g.append(line("M -40 -606 Q -10 -616 20 -608", 4, "#fff2b8"))
    if santa:
        g.append(santa_hat(0, -604, 78, 130, -12))
    if wafuku:   # 大きな花の髪飾り（成人式のギャルふう）
        g.append(flowers([(-58, -610)], 44, "#ff4f8b") + flowers([(-20, -636)], 28, "#ffffff", "#ff4f8b") + flowers([(-92, -578)], 24, "#e3b341", "#ffffff"))
    # ハートの髪留め
    g.append(path("M 50 -600 C 44 -612 30 -604 38 -592 L 50 -580 L 62 -592 C 70 -604 56 -612 50 -600 Z", "#ff4f8b", 3))
    # 目（まつげ多め）
    for s in (-1, 1):
        x = s * 27
        g.append(f'<ellipse cx="{x}" cy="-552" rx="17" ry="9" fill="#ff9ac4" opacity="0.5"/>')
        g.append(ellipse(x, -540, 14, 16, "#ffffff", 3))
        ix = x + s * -1 - (5 if look else 0)
        g.append(f'<circle cx="{ix}" cy="-538" r="10" fill="#5a3320"/><circle cx="{ix}" cy="-538" r="5" fill="{OL}"/>'
                 f'<circle cx="{ix - 3}" cy="-542" r="3.5" fill="#ffffff"/>')
        g.append(line(f"M {x - 17} -547 Q {x} -560 {x + 17} -549", 6))
        g.append(line(f"M {x + s * 16} -550 L {x + s * 25} -558", 3) + line(f"M {x + s * 13} -554 L {x + s * 19} -564", 3))
        g.append(line(f"M {x - 14} -576 Q {x} -583 {x + 14} -577", 3, "#b8863a"))
    g.append(line("M 0 -528 Q 4 -520 0 -516", 3, "#b9805a"))
    g.append(f'<ellipse cx="-46" cy="-514" rx="15" ry="9" fill="{CHEEK}" opacity="0.6"/>'
             f'<ellipse cx="46" cy="-514" rx="15" ry="9" fill="{CHEEK}" opacity="0.6"/>')
    if mouth == "open":
        g.append(shout_mouth(0, -506, 22, 30, "#9a2236", "#e2557a"))
    else:
        g.append(line("M -14 -500 Q 0 -494 14 -500", 5, "#e2557a"))
    return "".join(g)


# ---------- 舞台 ----------

def side_curtains():
    """左右の幕の形（path の d）と、留め紐の位置。キャラが袖から出入りするとき、この幕の後ろを通す。"""
    out = []
    for x0, edge in ((0, 250), (1670, 1670)):
        wave = " ".join(f"Q {edge + (12 if i % 2 else -12)} {130 + i * 110 + 55} {edge} {130 + i * 110 + 110}" for i in range(8))
        corner = 0 if x0 == 0 else W
        out.append((f"M {corner} 0 L {edge} 0 L {edge} 130 {wave} L {corner} 1010 Z", 200 if x0 == 0 else 1720))
    return out


def kadomatsu(x):
    """門松（床に置く。わらを巻いた台に、斜めに切った竹 3 本と松）。"""
    g = []
    for dx, top in ((-26, 700), (26, 668), (0, 630)):
        g.append(path(f"M {x + dx - 18} 900 L {x + dx - 18} {top + 22} L {x + dx + 18} {top} L {x + dx + 18} 900 Z", "#5aa864"))
        g.append(ellipse(x + dx, top + 11, 17, 8, "#d8efc8", 3))
        g.append(line(f"M {x + dx - 18} {top + 120} L {x + dx + 18} {top + 120}", 3, "#3d7a46"))
    g.append(bumpy([(x - 56, 820, 26), (x + 56, 816, 26), (x - 30, 800, 24), (x + 30, 798, 24), (x, 812, 26)], "#2f6b3a"))
    g.append(path(f"M {x - 64} 830 L {x + 64} 830 L {x + 56} 930 L {x - 56} 930 Z", "#c8a46a"))
    for y in (855, 885, 912):
        g.append(line(f"M {x - 60} {y} L {x + 60} {y}", 4, "#8a6a3a"))
    return "".join(g)


def shogatsu_deco():
    """お正月の回の飾り：上の幕の下のしめ縄と紙垂、壁の梅の花、両脇の門松。"""
    g = []
    for x, y, r in ((330, 270, 24), (560, 210, 18), (1380, 220, 20), (1600, 300, 26), (760, 320, 14), (1170, 300, 16),
                    (430, 440, 16), (1500, 460, 18)):
        g.append(flowers([(x, y)], r * 1.6, "#ff9ab8", "#ffe14d"))
    swag = "M 250 150 " + " ".join(f"Q {250 + i * 284 + 142} 220 {250 + (i + 1) * 284} 150" for i in range(5))
    g.append(f'<path d="{swag}" fill="none" stroke="{OL}" stroke-width="36" stroke-linecap="round"/>')
    g.append(f'<path d="{swag}" fill="none" stroke="#e2c27a" stroke-width="26" stroke-linecap="round"/>')
    g.append(f'<path d="{swag}" fill="none" stroke="#b8924a" stroke-width="26" stroke-dasharray="4 18" stroke-linecap="round"/>')
    for i in range(5):   # 紙垂（白いぎざぎざの紙）
        cx = 250 + i * 284 + 142
        for k in range(4):   # 互い違いに折れて下がる
            g.append(rrect(cx - 9 + (12 if k % 2 else 0), 184 + k * 24, 18, 26, 2, "#ffffff", 3))
    g.append(kadomatsu(330) + kadomatsu(1590))
    return "".join(g)


def xmas_deco():
    """クリスマスの回の飾り：壁の雪の結晶と、上の幕の下の緑のガーランド（赤と金の玉）。"""
    g = []
    for x, y, r in ((330, 260, 26), (560, 190, 18), (1380, 200, 22), (1600, 290, 28), (760, 300, 14), (1170, 280, 16),
                    (430, 430, 16), (1500, 450, 18)):
        for a in range(0, 180, 60):
            g.append(f'<g transform="rotate({a} {x} {y})">' + line(f"M {x - r} {y} L {x + r} {y}", 5, "#e9f2ff")
                     + line(f"M {x + r * 0.55} {y} L {x + r * 0.8} {y - r * 0.25} M {x + r * 0.55} {y} L {x + r * 0.8} {y + r * 0.25}", 3, "#e9f2ff")
                     + line(f"M {x - r * 0.55} {y} L {x - r * 0.8} {y - r * 0.25} M {x - r * 0.55} {y} L {x - r * 0.8} {y + r * 0.25}", 3, "#e9f2ff")
                     + "</g>")
    swag = "M 250 150 " + " ".join(f"Q {250 + i * 284 + 142} 230 {250 + (i + 1) * 284} 150" for i in range(5))
    g.append(f'<path d="{swag}" fill="none" stroke="#1d5e34" stroke-width="30" stroke-linecap="round"/>')
    g.append(f'<path d="{swag}" fill="none" stroke="#2f8f4e" stroke-width="16" stroke-dasharray="6 14" stroke-linecap="round"/>')
    for i in range(5):
        cx = 250 + i * 284 + 142
        g.append(circle(cx, 200, 15, "#d8343f" if i % 2 else "#e3b341", 4))
        g.append(path(f"M {cx} 158 l -22 -14 l 0 28 Z M {cx} 158 l 22 -14 l 0 28 Z", "#d8343f", 4))   # リボン
    return "".join(g)


def stage(special=None):
    """舞台。special は特別版の飾り（"xmas"＝クリスマス、"shogatsu"＝お正月）。"""
    defs = """<defs>
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1b1433"/><stop offset="1" stop-color="#432766"/></linearGradient>
<radialGradient id="burst" cx="0.5" cy="1" r="1"><stop offset="0" stop-color="#ffb3e6" stop-opacity="0.35"/><stop offset="1" stop-color="#ffb3e6" stop-opacity="0"/></radialGradient>
<linearGradient id="fold" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7d0c22"/><stop offset="0.45" stop-color="#c8193a"/><stop offset="0.6" stop-color="#d42a48"/><stop offset="1" stop-color="#7d0c22"/></linearGradient>
<pattern id="curtain" width="70" height="10" patternUnits="userSpaceOnUse"><rect width="70" height="10" fill="url(#fold)"/></pattern>
<linearGradient id="floor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9c5d33"/><stop offset="1" stop-color="#d79a5e"/></linearGradient>
<radialGradient id="spot" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#fff4c8" stop-opacity="0.75"/><stop offset="0.7" stop-color="#fff4c8" stop-opacity="0.25"/><stop offset="1" stop-color="#fff4c8" stop-opacity="0"/></radialGradient>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff8e0" stop-opacity="0.16"/><stop offset="1" stop-color="#fff8e0" stop-opacity="0.02"/></linearGradient>
</defs>"""
    g = [defs, f'<rect width="{W}" height="{H}" fill="url(#wall)"/>']
    cx, cy = 960, 780
    # 放射状の光と、電球のアーチ
    rays = ""
    for i in range(18):
        a0 = math.radians(180 + i * 10)
        a1 = math.radians(180 + i * 10 + 5)
        rays += (f'<path d="M {cx} {cy} L {cx + 1400 * math.cos(a0):.0f} {cy + 1400 * math.sin(a0):.0f} '
                 f'L {cx + 1400 * math.cos(a1):.0f} {cy + 1400 * math.sin(a1):.0f} Z" fill="#7a4fb0" opacity="0.25"/>')
    g.append(rays)
    g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="700" ry="620" fill="url(#burst)"/>')
    g.append(f'<path d="M {cx - 560} {cy} A 560 560 0 0 1 {cx + 560} {cy}" fill="none" stroke="#5a2f8a" stroke-width="44"/>')
    g.append(f'<path d="M {cx - 560} {cy} A 560 560 0 0 1 {cx + 560} {cy}" fill="none" stroke="#8b5cc4" stroke-width="6" transform="translate(0 0)"/>')
    for deg in range(180, 361, 8):
        a = math.radians(deg)
        x, y = cx + 560 * math.cos(a), cy + 560 * math.sin(a)
        g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="20" fill="#ffe9a0" opacity="0.25"/><circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="#fff3c4"/>')
    # 床（板目は奥へ向かって集まる）
    g.append(f'<rect x="0" y="760" width="{W}" height="250" fill="url(#floor)"/>')
    vx, vy = 960, 200
    for xb in range(-1200, 3200, 140):
        x760 = vx + (xb - vx) * (760 - vy) / (1010 - vy)
        g.append(f'<line x1="{x760:.0f}" y1="760" x2="{xb}" y2="1010" stroke="#8a5230" stroke-width="3" opacity="0.6"/>')
    for y in (800, 850, 915):
        g.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#8a5230" stroke-width="2" opacity="0.35"/>')
    g.append(f'<rect x="0" y="752" width="{W}" height="10" fill="#2a1a12"/>')
    g.append(f'<rect x="0" y="1008" width="{W}" height="{H - 1008}" fill="#24130d"/>')
    g.append(f'<rect x="0" y="1004" width="{W}" height="8" fill="#e3b341"/>')
    # スポットライト
    g.append('<path d="M 700 0 L 980 0 L 1260 960 L 560 960 Z" fill="url(#beam)"/>')
    g.append(f'<ellipse cx="960" cy="935" rx="{720 if special else 600}" ry="105" fill="url(#spot)"/>')
    if special:
        g.append({"xmas": xmas_deco, "shogatsu": shogatsu_deco}[special]())
    # 幕（左右と上）
    for d, tie_x in side_curtains():
        g.append(f'<path d="{d}" fill="url(#curtain)" stroke="#4a0614" stroke-width="4"/>')
        g.append(f'<rect x="{tie_x - 40}" y="560" width="80" height="24" rx="12" fill="#e3b341" stroke="#8a6414" stroke-width="3"/>')
    top = f'<path d="M 0 0 L {W} 0 L {W} 110 ' + " ".join(
        f"Q {W - i * 120 - 60} 170 {W - (i + 1) * 120} 110" for i in range(16)) + ' Z" fill="url(#curtain)" stroke="#4a0614" stroke-width="4"/>'
    g.append(top)
    g.append('<path d="M 0 110 ' + " ".join(f"Q {i * 120 + 60} 170 {(i + 1) * 120} 110" for i in range(16))
             + '" fill="none" stroke="#e3b341" stroke-width="8"/>')
    return "".join(g)


def mic(x, head_y):
    """センターマイク。スタンドの台、細い支柱、角の丸いマイク。"""
    g = [ellipse(x, FLOOR_Y + 2, 58, 13, "#3a3a46", 4)]
    g.append(f'<rect x="{x - 5}" y="{head_y + 30}" width="10" height="{FLOOR_Y - head_y - 30}" {st("#c8ccd6", 3)}/>')
    g.append(rrect(x - 12, head_y + 22, 24, 22, 5, "#5a5d6a", 3))
    g.append(rrect(x - 24, head_y - 52, 48, 82, 20, "#d9dde5", 4))
    for i in range(5):
        y = head_y - 38 + i * 9
        g.append(f'<line x1="{x - 15}" y1="{y}" x2="{x + 15}" y2="{y}" stroke="#9aa0ad" stroke-width="2.5"/>')
    g.append(f'<rect x="{x - 24}" y="{head_y + 6}" width="48" height="10" fill="#6c7080"/>')
    return "".join(g)


def impact():
    """ツッコミが当たったところに出す、ぎざぎざの星（中心が (0, 0)）。"""
    def star(r_out, r_in, n=14, rot=8):
        pts = []
        for i in range(n * 2):
            r = r_out if i % 2 == 0 else r_in
            a = math.radians(rot + i * 180 / n)
            pts.append(f"{r * math.cos(a):.1f},{r * math.sin(a):.1f}")
        return " ".join(pts)
    out = f'<polygon points="{star(92, 40)}" fill="#ffe14d" stroke="#f08a24" stroke-width="7" stroke-linejoin="round"/>'
    out += f'<polygon points="{star(46, 22, 10, 20)}" fill="#ffffff"/>'
    for a in (200, 225, 250):
        x0, y0 = 110 * math.cos(math.radians(a)), 110 * math.sin(math.radians(a))
        x1, y1 = 150 * math.cos(math.radians(a)), 150 * math.sin(math.radians(a))
        out += f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="#ffffff" stroke-width="7" stroke-linecap="round"/>'
    return out


def place(svg, x, y=FLOOR_Y, scale=1.0, flip=False):
    sx = -scale if flip else scale
    shadow = f'<ellipse cx="{x}" cy="{y + 4}" rx="{120 * scale}" ry="{18 * scale}" fill="#000" opacity="0.22"/>'
    return shadow + f'<g transform="translate({x} {y}) scale({sx} {scale})">{svg}</g>'


def doc(body, w=W, h=H, bg=None):
    back = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{back}{body}</svg>'


# ---------- 書き出し ----------

def browser():
    for p in [os.environ.get("CHROME", ""), shutil.which("chrome") or "",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]:
        if p and Path(p).exists():
            return p
    raise SystemExit("PNG に書き出すための Chrome / Edge が見つからない")


def to_png(svg_path, w, h, transparent=False):
    png = svg_path.with_suffix(".png")
    profile = OUT / ".chrome"
    bg = ["--default-background-color=00000000"] if transparent else []
    subprocess.run([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}", *bg,
                    f"--window-size={w},{h}", f"--screenshot={png}", svg_path.resolve().as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    return png


def write(name, svg, w=W, h=H, transparent=False):
    p = OUT / f"{name}.svg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg, encoding="utf-8")
    print(to_png(p, w, h, transparent))


# 動画で重ねる部品。キャラは 1000x1000 の透明な画像に、足元を (500, 960) にして置く
SPRITE = 1000
SPRITE_FEET = (500, 960)
COMBOS = {
    "male": {"boke": male_boke, "tsukkomi": male_tsukkomi, "mic_y": 390, "x": (770, 1165)},
    "female": {"boke": female_boke, "tsukkomi": female_tsukkomi, "mic_y": 560, "x": (790, 1140)},
}
# 特別版（4 人）。4 人が並ぶよう 0.75 倍で描き、男のコンビを左、女のコンビを右に、それぞれのマイクの前に立たせる。
# x は proto/render.py の COMBOS["xmas"] と同じ。部品の名前は m／f（男／女）＋ boke／tsukkomi
FOUR_SCALE = 0.75
FOUR = {"m": {"boke": male_boke, "tsukkomi": male_tsukkomi, "x": (470, 766), "mic_x": 618, "mic_h": 540},
        "f": {"boke": female_boke, "tsukkomi": female_tsukkomi, "x": (1150, 1412), "mic_x": 1281, "mic_h": 370}}
SPECIALS = {"xmas": "santa", "shogatsu": "wafuku"}   # 特別版の名前（台本の combo:・部品のフォルダ・舞台の飾り）→ 衣装
# 末尾に "look" が付くものは相手を見る顔（見つめ合う間と、そのあとのセリフで使う）
SPRITE_POSES = {"boke": [("stand", "closed"), ("stand", "open"), ("hit1", "open"), ("hit", "open"), ("hit3", "open"), ("stand", "closed", "look"), ("stand", "open", "look")],
                "tsukkomi": [("stand", "closed"), ("stand", "open"), ("tsukkomi", "closed"), ("tsukkomi", "open"),
                             ("stand", "closed", "look"), ("stand", "open", "look")]}


def sprites():
    fx, fy = SPRITE_FEET
    for combo, c in COMBOS.items():
        write(f"sprites/{combo}/bg", doc(stage() + mic(960, c["mic_y"])))
        # 左右の幕だけ（キャラの上に重ねる。袖から出入りするとき幕の後ろを通るように）
        clip = "".join(f'<path d="{d}"/>' for d, _ in side_curtains())
        front = f'<defs><clipPath id="sides">{clip}<rect x="0" y="0" width="1" height="1"/></clipPath></defs><g clip-path="url(#sides)">{stage()}</g>'
        write(f"sprites/{combo}/curtain_front", doc(front), W, H, True)
        for role, poses in SPRITE_POSES.items():
            for pose, mouth, *look in poses:
                body = f'<g transform="translate({fx} {fy})">{c[role](mouth, pose, bool(look))}</g>'
                name = f"{role}_{pose}_{mouth}" + ("_look" if look else "")
                write(f"sprites/{combo}/{name}", doc(body, SPRITE, SPRITE), SPRITE, SPRITE, True)
    write("sprites/impact", doc(f'<g transform="translate(160 160)">{impact()}</g>', 320, 320), 320, 320, True)
    for special in SPECIALS:
        special_sprites(special)


def special_stage(special):
    return stage(special) + "".join(mic(c["mic_x"], FLOOR_Y - round(c["mic_h"] * FOUR_SCALE)) for c in FOUR.values())


def special_sprites(special):
    """特別版の部品（build/art/sprites/<special>/）。"""
    fx, fy = SPRITE_FEET
    costume = SPECIALS[special]
    write(f"sprites/{special}/bg", doc(special_stage(special)))
    clip = "".join(f'<path d="{d}"/>' for d, _ in side_curtains())
    front = f'<defs><clipPath id="sides">{clip}<rect x="0" y="0" width="1" height="1"/></clipPath></defs><g clip-path="url(#sides)">{stage(special)}</g>'
    write(f"sprites/{special}/curtain_front", doc(front), W, H, True)
    for kind, c in FOUR.items():
        for role, poses in SPRITE_POSES.items():
            for pose, mouth, *look in poses:
                body = f'<g transform="translate({fx} {fy}) scale({FOUR_SCALE})">{c[role](mouth, pose, bool(look), costume=costume)}</g>'
                name = f"{kind}{role}_{pose}_{mouth}" + ("_look" if look else "")
                write(f"sprites/{special}/{name}", doc(body, SPRITE, SPRITE), SPRITE, SPRITE, True)


def main():
    write("stage", doc(stage()))
    write("combo_male", doc(stage() + mic(960, 390)
                            + place(male_boke("closed"), 770) + place(male_tsukkomi("open", "tsukkomi"), 1165)))
    write("combo_female", doc(stage() + mic(960, 560)
                              + place(female_boke("closed"), 790, scale=1.0) + place(female_tsukkomi("open", "tsukkomi"), 1140)))
    # 4 人の口を閉じた顔・開けた顔
    sw, sh, sc = 1920, 700, 0.72
    body = ""
    chars = [(male_boke, 162), (male_tsukkomi, 186), (female_boke, 76), (female_tsukkomi, 152)]  # 横幅の半分
    x = 50
    for fn, half in chars:
        for m in ("closed", "open"):
            x += half * sc
            body += place(fn(m, "stand"), x, 670, sc)
            x += half * sc + 22
    write("sheet", doc(body, sw, sh, "#f3eee6"), sw, sh)
    for special in SPECIALS:
        special_preview(special)
    sprites()


def special_preview(special):
    """特別版の 4 人の並び（確かめる用。build/art/combo_<special>.png）。"""
    costume = SPECIALS[special]
    write(f"combo_{special}", doc(special_stage(special) + "".join(
        place(c["boke"]("closed", costume=costume), c["x"][0], scale=FOUR_SCALE)
        + place(c["tsukkomi"]("open", "tsukkomi", costume=costume), c["x"][1], scale=FOUR_SCALE)
        for c in FOUR.values())))


if __name__ == "__main__":
    import sys
    if sys.argv[1:] and sys.argv[1] in SPECIALS:   # 特別版の絵だけ：python art/gen_chars.py shogatsu [preview]
        special_preview(sys.argv[1])
        if sys.argv[2:] != ["preview"]:
            special_sprites(sys.argv[1])
    else:
        main()
