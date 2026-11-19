# CLAUDE.md — 時事漫才動画（JijiManzai）

時事の話題を、決まったコンビ 2 組（男性・女性）の漫才にして動画にする。いまは試作の段階（`proto/` と `art/`）。
先行して作った童話パロディ動画の仕組み（`Z:/git/Movie/BlackFairyTales`）を参考にしている。

## 守ること

動画 3 つに共通する決まり（進め方・声・書き出しの罠・YouTube・Windows の罠）は、親フォルダの `Z:\git\Movie\CLAUDE.md`（自動で読まれる）。ここにはこの作品のことだけを書く。

- **漫才の台本を書く・直すときは、先に [docs/SCRIPT_GUIDE.md](docs/SCRIPT_GUIDE.md) を読む**（決まりごとと、使える漫才の技）
- **読み間違いのリストは BlackFairyTales と共通**（`Z:/git/Movie/BlackFairyTales/tools/config.json` の `readings.ja`。synth.py が読む）。ここで見つけた・指摘された読み間違いも、そのリストに足す。漫才だけで使う読み替えは `proto/voices.json` の `readings`
- **声は VOICEVOX でも作れる**（`--backend voicevox`。アプリを起動しておく）。配役と調整は `proto/voices.json` の `voicevox`、キャラの規約とクレジット表記は [docs/VOICEVOX.md](docs/VOICEVOX.md)。VOICEVOX は読む前に読みをカナで返すので、`proto/vv_kana.py` で全行の読みを書き出して読み間違いを確かめる
- **動画は、利用者が「動画を作って」と言うまで作らない**（音声の試作はしてよい）。動画を作るときの決まり（吹き出しは声に合わせて字を出す、YouTube の字幕は付けない、叩く強さで飛び方・折れ方を変える、締めのあいさつに小さな拍手）は [docs/VIDEO_GUIDE.md](docs/VIDEO_GUIDE.md)。確かめるのは `render.py --frames` の静止画でよい
- **YouTube に上げる手順**（チャンネルの作り方、1 本ごとの手順、mp4 の形式、収益化の注意、まだ作っていない仕組み）は [docs/YOUTUBE.md](docs/YOUTUBE.md)。BlackFairyTales（毒入り童話）の手順を元にしている
- 台本は `scripts/`（直すのは `.txt`、読む用の `.md` は `proto/script_md.py` で作る）。前の台本は `proto/` にある
- 動画の形は決まっている：タイトル（題名とお題）→ 2 人が袖から登場 → 漫才（3 分以内）→ 袖へ退場 → エンディング（名場面を流しながら、2 人の声でチャンネル登録を頼む。形は固定で、ボケのひとことだけ回ごとに変える）
- **特別版**（クリスマス・お正月など）は 2 組そろって 4 人（`combo: xmas` / `shogatsu`）、衣装も回に合わせ、動画全体が 8 分を超える長尺（途中に広告）。書き方は [docs/SCRIPT_GUIDE.md](docs/SCRIPT_GUIDE.md)、絵と動画は [docs/VIDEO_GUIDE.md](docs/VIDEO_GUIDE.md)
- **PC を移るとき**の準備（入れるソフト・キー・予定のタスクの作り直し・git に入っているもの）は [docs/SETUP.md](docs/SETUP.md)
- 親フォルダの `Z:\git\Movie\CLAUDE.md` は git に入っていないので、写しを [docs/parent_CLAUDE.md](docs/parent_CLAUDE.md) に置いている。**親の CLAUDE.md を直したら、写しも同じに直す**

## 運用の決まり（利用者から言われたこと）

- **commit と push は聞かずにやる**（2026-11-04 利用者「コミットのタイミングだと思うところで、コミットとプッシュを同時に」）。台本を書き終えた、予定を組み直して KEYWORDS.md・docs を直した、など 1 つの作業がまとまったら commit → `git push origin main`。声や動画を作っている途中、Studio の結果を待っている間には切らない。報告には commit の番号と新しいファイルを書く。**BlackFairyTales（読み替えのリスト）も、要ると思ったときに commit・push してよい**（2026-11-19 利用者「今後、コミットとプッシュはあなたが必要だと思う時に適時」）。ただし BlackFairyTales のほかのセッションの変更は混ぜない（自分が直したファイルだけ add する）
- **公開の枠**：本編は**月・金 19:00**、**水曜 19:00 は時事の新作の枠**（2026-11-04 利用者）、**火・木 19:00 は都道府県シリーズの枠**（2026-11-19 利用者。順はランダム、再生リスト「都道府県の話題」）。ショートは本編の翌日 12:00（再生リストに入れない）。いつでもよい回は月・金の予定の最後に足し、時事の回は空いている直近の水曜に入れる。毎年ある行事は YouTube の題名に年を付ける。予定と経緯は [docs/YOUTUBE.md](docs/YOUTUBE.md)、日付は KEYWORDS.md の表
- **YouTube Studio の操作は Sonnet に任せる**（2026-11-04 利用者「YotubeStudioの操作は、Sonnetで」）。Agent ツール（model: sonnet）に、やることの一覧（`build/work/` の JSON。1 件ごとの done のフラグ付き）と、操作のこつ（docs/YOUTUBE.md、`docs/briefs/studio.md` のひな形）を渡す。1 回に頼むのは本編なら 10 本くらいまで（多いと途中で止まる）。結果は一覧と Studio で確かめてから KEYWORDS.md を `tools/set_date.py`・`tools/set_short.py` で直す。動画ファイルは 10MB を超えるので、アップロードの画面でファイルを選ぶのは利用者
- **ショートの関連動画**は、予定のタスク `shorts-related-video`（月・火・木・金 13:00。ほのぼの漫才劇場・毒入り童話・BlackFairyTales 英語の 3 チャンネル）が本編の公開後に付ける。中身の写しは [docs/scheduled/shorts-related-video.md](docs/scheduled/shorts-related-video.md)（直したら写しも直す）

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
tools/               KEYWORDS.md の表を直す道具（set_date・set_short・tick・number_keywords）、ショートの説明文の下書き（mk_short）、説明文を読む（yt）、まとめて書き出す（render_batch）
docs/scheduled/      予定のタスクの中身の写し（PC を移ったら作り直す）
build/               出力（git の外。ただし各回の説明文 build/<番号>_<名前>/youtube.txt・youtube_short.txt だけは git に入れる）
```

```bash
python art/gen_chars.py                # 絵と部品（絵を変えたときだけ）
python proto/synth.py scripts/<番号>_<名前>.txt --backend voicevox      # 声とタイムライン
python proto/synth.py scripts/<番号>_<名前>_end.txt --backend voicevox  # その回のエンディングの声
python proto/render.py <番号>_<名前>   # 動画（build/anim/<番号>_<名前>.mp4）
python tools/render_batch.py <番号>_<名前> ... -j 2   # 動画・ショート・サムネイルをまとめて
python tools/set_date.py <番号> <YYYY/MM/DD>          # KEYWORDS.md の予約日（ショートは tools/set_short.py、動画の○は tools/tick.py）
```
