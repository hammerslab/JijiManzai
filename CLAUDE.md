# CLAUDE.md — 時事漫才動画（JijiManzai）

時事の話題を、決まったコンビ 2 組（男性・女性）の漫才にして動画にする。いまは試作の段階（`proto/` と `art/`）。
先行して作った童話パロディ動画の仕組み（`Z:/git/BlackFairyTales`）を参考にしている。

## 守ること

- 返事・報告・コメントは日本語
- **漫才の台本を書く・直すときは、先に [docs/SCRIPT_GUIDE.md](docs/SCRIPT_GUIDE.md) を読む**（決まりごとと、使える漫才の技）
- 音は聴けないので、声の出来は利用者に聴いて判断してもらう。長さ・音量・音割れは測って確かめる
- 書き出した動画は、コマを開いて目で見る
- **読み間違いのリストは BlackFairyTales と共通**（`Z:/git/BlackFairyTales/tools/config.json` の `readings.ja`。synth.py が読む）。ここで見つけた・指摘された読み間違いも、そのリストに足す。漫才だけで使う読み替えは `proto/voices.json` の `readings`
- **声は VOICEVOX でも作れる**（`--backend voicevox`。アプリを起動しておく）。配役と調整は `proto/voices.json` の `voicevox`、キャラの規約とクレジット表記は [docs/VOICEVOX.md](docs/VOICEVOX.md)。VOICEVOX は読む前に読みをカナで返すので、`proto/vv_kana.py` で全行の読みを書き出して読み間違いを確かめる
- **動画は、利用者が「動画を作って」と言うまで作らない**（音声の試作はしてよい）。動画を作るときの決まり（吹き出しは声に合わせて字を出す、YouTube の字幕は付けない、叩く強さで飛び方・折れ方を変える、締めのあいさつに小さな拍手）は [docs/VIDEO_GUIDE.md](docs/VIDEO_GUIDE.md)。確かめるのは `render.py --frames` の静止画でよい
- **YouTube に上げる手順**（チャンネルの作り方、1 本ごとの手順、mp4 の形式、収益化の注意、まだ作っていない仕組み）は [docs/YOUTUBE.md](docs/YOUTUBE.md)。BlackFairyTales（毒入り童話）の手順を元にしている
- 台本は `scripts/`（直すのは `.txt`、読む用の `.md` は `proto/script_md.py` で作る）。前の台本は `proto/` にある
- 動画の形は決まっている：タイトル（題名とお題）→ 2 人が袖から登場 → 漫才（3 分以内）→ 袖へ退場 → エンディング（名場面を流しながら、2 人の声でチャンネル登録を頼む。形は固定で、ボケのひとことだけ回ごとに変える）

## 構成

```
scripts/<番号>_<名前>.txt  台本（書き方は proto/hacker.txt の頭）。名前はすべて `<番号>_<名前>`（4 桁の番号、例 0001_m1）。番号は台本を作った時点で KEYWORDS.md のキーワードに付ける（scripts/README.md）
proto/ending_*.txt   エンディングの共通の台本（male / female）。回ごとの scripts/<題材>_end.txt がない回に使う
scripts/<番号>_<名前>_end.txt  その回のエンディング（ボケのひとことを変えたもの）。synth.py で build/<番号>_<名前>_end/ に声を作ると render.py が使う
proto/voices.json    声の設定（コンビごとの声、「」の声の変え方、叩くツッコミ、読み替え）
proto/synth.py       台本 → 声（Google Cloud TTS の Chirp 3: HD）→ 間を入れて 1 本の音声に。動画用のタイムライン（timeline_chirp.json）も書き出す
proto/vv_compare.py  VOICEVOX の声の聴き比べ（役ごと）／proto/vv_pairs.py コンビの組み合わせ・調整の聴き比べ（本番の台本の頭で）
proto/vv_kana.py     VOICEVOX が台本をどう読むかをカナで書き出す（build/kana/）
proto/gen_sfx.py     効果音（手刀・拍手）と出囃子を作る（assets/audio/）
proto/render.py      台本 1 本を決まった形の動画に（口パク・叩くツッコミ・見つめ合う・登場と退場・エンディング。--from/--to で一部だけ、--main-only で漫才だけ）
art/gen_chars.py     舞台とキャラの絵（SVG）→ PNG と動画用の部品（袖の幕は前に重ねる部品も）
assets/fonts         題名の字（Zen Maru Gothic・OFL。BlackFairyTales と同じ）
KEYWORDS.md          題材に使えるキーワードの一覧
build/               出力
```

```bash
python art/gen_chars.py                # 絵と部品（絵を変えたときだけ）
python proto/synth.py scripts/<番号>_<名前>.txt --backend voicevox      # 声とタイムライン
python proto/synth.py scripts/<番号>_<名前>_end.txt --backend voicevox  # その回のエンディングの声
python proto/render.py <番号>_<名前>   # 動画（build/anim/<番号>_<名前>.mp4）
```
