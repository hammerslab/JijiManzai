"""youtube.txt を読んで、アップロードに入れる値を JSON で出す。python tools/yt.py 0006"""
import json, re, sys, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
n = sys.argv[1]
p = glob.glob(str(ROOT / "build" / f"{n}_*" / "youtube.txt"))[0]
s = open(p, encoding="utf-8").read()
sec = dict(re.findall(r"■ ([^\n（]+)[^\n]*\n(.*?)(?=\n■ |\Z)", s, re.S))
d = re.search(r"(\d{4})/(\d{2})/(\d{2})", sec["公開"])
print(json.dumps({"title": sec["タイトル"].strip(), "desc": sec["説明"].strip(), "tags": sec["タグ"].strip() + ",",
                  "playlist": sec["再生リスト"].strip(), "date": "/".join(d.groups())}, ensure_ascii=False))
