"""KEYWORDS.md の表で YouTube に日付があり、ショートが「未」の回について、youtube.txt から youtube_short.txt（ショートの下書き）を作る。python tools/mk_short.py  → 公開日の順に番号を出す"""
import re, glob, datetime as dt
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import kw
order = []
for num, (_, r) in kw.load()[1].items():
    m = re.match(r"^(予約|公開済み) (\d{4})/(\d{2})/(\d{2})$", r["YouTube"])
    if m and r["動画"] == "○" and r["ショート"] == "未":
        order.append((dt.date(int(m[2]), int(m[3]), int(m[4])), num))
order.sort()
for d, n in order:
    p = glob.glob(str(ROOT / "build" / f"{n}_*" / "youtube.txt"))[0]
    s = Path(p).read_text(encoding="utf-8")
    sec = dict(re.findall(r"■ ([^\n（]+)[^\n]*\n(.*?)(?=\n■ |\Z)", s, re.S))
    title = sec["タイトル"].strip()
    m = re.match(r"(.+?)【ほのぼの漫才】(.+)", title)
    catch, theme = m[1], m[2]
    desc = sec["説明"].strip().split("\n")
    first = desc[0]
    notes = [x for x in desc if x.startswith("※")]
    credit = [x for x in desc if x.startswith("音声：")][0]
    st = f"{theme}！ {catch} #shorts"
    body = "\n".join([first] + notes + ["続きは本編で。", "", "#漫才 #お笑い #ほのぼの漫才劇場 #shorts", "", credit])
    pub = d + dt.timedelta(1)
    out = f"""■ タイトル
{st}

■ 説明
{body}

■ 再生リスト
なし（ショートは入れない）

■ 関連動画
{title}（本編）

■ 公開
{pub.year}/{pub.month:02d}/{pub.day:02d} 12:00 予約

■ ファイル
build/anim/{Path(p).parent.name}_short.mp4
"""
    Path(p).with_name("youtube_short.txt").write_text(out, encoding="utf-8", newline="\n")
    print(n, pub.isoformat(), st)
