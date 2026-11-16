# HammersLab 動画のルール（YouTube・Instagram 向けの動画づくり）

`Z:\git\Movie\` の下にあるリポジトリは、このファイルを自動で読む（Claude Code は親フォルダの CLAUDE.md を読む）。
ここには 3 つの動画のリポジトリに共通することだけを書く。作品ごとの決まりは、それぞれの CLAUDE.md と `docs/`。
アプリやゲームのルール（`Z:\git\MyApp\`・`Z:\git\MyGame\`）は自動では読まれない。要るところだけ下の「参考」から開く。

| リポジトリ | 何か | 声 |
|---|---|---|
| `BlackFairyTales` | 童話を下敷きにした大人向けブラックコメディ（Godot のドット絵アニメ・多言語）| Google Cloud TTS |
| `JijiManzai` | 時事の話題を、決まったコンビ 2 組の漫才に | Google Cloud TTS / VOICEVOX |
| `HammersLabPromo` | 自分のアプリ（jp.hammerslab.*）の宣伝。YouTube と Instagram | Google Cloud TTS（VOICEVOX は使わない）|

仕組みは BlackFairyTales が最初に作り、JijiManzai がそれを参考にし、HammersLabPromo は両方を参考にしている。
直すときは、ほかの 2 つに同じ仕組みがないかを見る（片方だけ直して、もう片方に同じ穴が残らないように）。

---

## 1. 進め方

- 返事・報告・コメント・コミットメッセージは日本語。報告は「変えたこと / 確かめた結果 / 残っていること」だけ
- 要求が明確なら、確認を挟まずに進める。長い前置き・念のための確認・求められていないリスクの説明はしない
- ⚠ **音は聴けない。** 声や曲の出来は利用者に聴いて判断してもらう（そう伝える）。長さ・音量・音割れは測って確かめる
- ⚠ **描いた絵と書き出した動画は、必ずコマを開いて目で見る。** 数値やログだけで「できた」にしない
- 新しく作ったファイルは、その場で `git add` する

---

## 2. 声（TTS）

- 本番は **Google Cloud Text-to-Speech の Chirp 3: HD**（声の名前は `ja-JP-Chirp3-HD-<名前>`）。
  声の高さは API で変えられないので `pitch` は ffmpeg で、話す速さは `speakingRate`。同じ声を使い回すときは速さと高さで差をつける
- API キーは `C:\Users\tomihama\Documents\個人用\アプリのKey\Movie\.env` に置く（3 つのリポジトリで共通。PC を替えても消えない「アプリのKey」のフォルダ。コードは `Path.home()` から探す）。git に入れない。⚠ キーをチャット・ログ・コミットに出さない
- ⚠ **読み間違いのリストは共通で 1 つ**: `Z:\git\Movie\BlackFairyTales\tools\config.json` の `readings.ja`。
  どのリポジトリで見つけた・指摘された読み間違いも、ここに足す。そのリポジトリだけで使う読み替えは、それぞれの設定に置く
- 読みは声を作る前にカナで確かめる（OpenJTalk の読みは目安。Google の読みと違うこともある。VOICEVOX は読みをカナで返す）
- 声の大きさはそろえる（BlackFairyTales は -16 LUFS にそろえてからキャッシュ）
- VOICEVOX を使うときは、キャラの規約とクレジット表記を守る（`JijiManzai/docs/VOICEVOX.md`）

---

## 3. 書き出し（Godot・ffmpeg）

- Godot 4.7.2 と FFmpeg は winget で入れたもの（`GODOT` / `FFMPEG` の環境変数で上書きできる）
- `stretch/mode` は `canvas_items`（`viewport` だと小さい解像度で字を描いてから拡大するので、小さい字がつぶれる）
- ⚠ **Movie Maker は、ドライブや CPU が混んでいると、絵を描かずに前のコマを書き続ける**（最初の数秒のあと絵が止まった mp4 ができる。エラーは出ない）。
  2026-11-11 には、時事漫才の書き出しと VOICEVOX が同時に動いていて BlackFairyTales の書き出しが止まった。
  → **ほかのリポジトリの重い書き出しや VOICEVOX が動いている間は流さない**。コマは Z: ではなく `%TEMP%` の下に置き、動画にする前に「コマが固まっていないか」を確かめる
- Movie Maker は `--resolution` を無視して、プロジェクトの窓の大きさで記録する（写しの `override.cfg` で大きさを決める）
- ffmpeg に `-shortest` を付けない（字幕のトラックの終わりで動画が切れる）
- GDScript で辞書・配列から取った値に `:=` を使わない（`var k: float = ...`）。構文の誤りがある Godot は終わらずに残る → 止めたら `Get-Process Godot*` を見る。
  止めるときは名前で全部止めず、`CommandLine` に自分のリポジトリ名を含むものだけ（ほかのリポジトリの書き出しを落とさない）

---

## 4. YouTube・著作権

- 題名の字は **Zen Maru Gothic**（OFL）。フォントは映像に表記の義務がないので書かない。表記が利用条件の音声（VOICEVOX など）を使うときだけ、その表記を足す
- ⚠ 実在のブランド・人物、有名な映像化の見た目・名前・歌・独自の場面を出さない。画面録画に写る、よそのサイト名・見出しにも気をつける
- 収益化の注意・投稿の手順は、それぞれの `docs/`（BlackFairyTales `docs/PLAN.md`、JijiManzai `docs/YOUTUBE.md`）。新しい仕組みを足したら、ほかのリポジトリの手順にも要るかを見る

---

## 5. Windows の罠（動画で踏んだもの）

- PowerShell 5.1 は BOM なしの UTF-8 の `.ps1` を Shift-JIS として読む → `.ps1` は ASCII だけで書く
- PowerShell の `Out-File -Encoding utf8` は BOM を付ける → Python で読む JSON は `utf-8-sig` で開く
- 日本語をシェルの引数に直接置かない。逆斜線を含むコードをヒアドキュメントで書かない（Write / Edit で直接書く）
- Kokoro（ローカルの TTS）は Python 3.12 の `.venv` で動かす（3.13 は古い numpy のビルドで失敗する。入れ方は BlackFairyTales の CLAUDE.md）

---

## 参考（自動では読まれない）

- Windows・シェル・Git の罠の全体: `Z:\git\MyApp\COMMON.md`「Windows / シェルの罠」「Git と作業の進め方」
- Godot・フォントの知見: `Z:\git\MyGame\CLAUDE.md`（§3-4 フォント、§12 Godot / ツールの罠）
- 宣伝するアプリのコードとストアの説明: `Z:\git\MyApp\<名前>`・`Z:\git\MyGame\<名前>`（一覧は `HammersLabPromo/docs/APPS.md`）
