# 新しい PC の準備（PC を移るとき）

このリポジトリは、CLAUDE.md と docs/ だけで作り方が分かるようにしてある。PC を移るときは、ここに書いたものを用意すれば続けられる（2026-11-16）。

## git に入っているもの・入っていないもの

| もの | 場所 | git | 移るとき |
|---|---|---|---|
| 台本・エンディング・読む用の md | `scripts/` | 入っている | そのまま |
| 一覧（キーワード・予約日） | `KEYWORDS.md`・`scripts/README.md` | 入っている | そのまま |
| 仕組み（声・絵・動画・ショート・サムネイル） | `proto/`・`art/` | 入っている | そのまま |
| 台帳を直す道具・まとめて書き出す道具 | `tools/`（set_date・set_short・tick・mk_short・yt・number_keywords・render_batch） | 入っている | そのまま |
| 各回の説明文 | `build/<番号>_<名前>/youtube.txt`・`youtube_short.txt` | **入っている**（`.gitignore` で、build/ の中でこれだけ入れている） | そのまま |
| 予定のタスクの中身 | `docs/scheduled/`（写し） | 入っている | 下の「予定のタスク」で作り直す |
| 声・絵の部品・動画・ショート・サムネイル・コマ | `build/` | 入っていない | 作り直せる（下の「作り直し」）。まだ上げていない回の動画は、移すか作り直す |
| Studio の作業の一覧（動画 ID など）・ログ | `build/work/` | 入っていない | なくても困らない（ID は Studio で探せる） |
| API キー | `アプリのKey\Movie\.env` | 入っていない | 「アプリのKey」のフォルダにあるので、PC を替えても残る（下の「キー」） |

## フォルダの場所

`Z:\git\Movie\JijiManzai` と `Z:\git\Movie\BlackFairyTales` に置く（別の場所にするなら、`proto/synth.py` の `BFT` と、予定のタスクの中のパスを直す）。読み間違いの共通のリストは BlackFairyTales 側にあるので、**2 つともクローンする**。親フォルダの `Z:\git\Movie\CLAUDE.md` も要る。

## 入れるもの

| もの | 使うところ | 入れ方・メモ |
|---|---|---|
| Python 3.13 と numpy・Pillow | すべての道具 | `pip install numpy pillow`（2026-11 時点で numpy 2.2・Pillow 12） |
| FFmpeg | 声のつなぎ・動画 | `winget install Gyan.FFmpeg`（PATH になければ synth.py が winget の場所を探す） |
| VOICEVOX | 声（本番の声） | `C:\Program Files\VOICEVOX\VOICEVOX.exe`。アプリを起動しておくと `http://127.0.0.1:50021` で使える（別の場所なら環境変数 `VOICEVOX_URL`）。キャラの規約は docs/VOICEVOX.md |
| Chrome か Edge | 絵（SVG → PNG）の書き出し | `art/gen_chars.py` が探す（別の場所なら環境変数 `CHROME`） |
| BIZ UDゴシック | 吹き出し・サムネイルの字 | Windows に入っているフォント（`C:\Windows\Fonts\BIZ-UDGothicB.ttc`） |
| Claude in Chrome（拡張機能） | YouTube Studio の操作 | Chrome に入れ、YouTube の 3 チャンネル（ほのぼの漫才劇場・毒入り童話・BlackFairyTales）を切り替えられるアカウントでログインしておく |

## キー

- Google の音声合成（Chirp 3: HD。いまの本番は VOICEVOX なので、Google の声を作るときだけ要る）：`GOOGLE_TTS_API_KEY`。`C:\Users\tomihama\Documents\個人用\アプリのKey\Movie\.env` に書く（動画 3 つで共通。古い場所の BlackFairyTales やこのリポジトリの `.env` も読む）。**キーはチャット・ログ・コミットに出さない**

## 作り直し

```bash
python art/gen_chars.py                               # 絵の部品（build/art/。特別版の xmas・shogatsu も）
python proto/synth.py scripts/<番号>_<名前>.txt --backend voicevox       # 声
python proto/synth.py scripts/<番号>_<名前>_end.txt --backend voicevox   # エンディングの声
python tools/render_batch.py <番号>_<名前> ... -j 2   # 動画・ショート・サムネイル
```
効果音と出囃子（`assets/audio/`）は git に入っている（作り直すなら `python proto/gen_sfx.py`）。

## 予定のタスク（この PC のアプリに入っているので、新しい PC で作り直す）

| タスク | いつ | 中身の写し |
|---|---|---|
| shorts-related-video | 月・火・木・金 13:00 | `docs/scheduled/shorts-related-video.md` |

Claude Code のアプリで「この写しの中身で、同じ名前・同じ時刻の予定のタスクを作って」と頼む。作ったら一度「Run now」で動かし、Chrome の操作などを許可しておく（次からは確認で止まらない）。中身を直したら、写しも直す。

## Claude のメモリ

メモリ（`C:\Users\<ユーザー>\.claude\projects\...\memory\`）は PC ごとで、移らない。いま使っている決まりは CLAUDE.md と docs に書いてあるので、メモリがなくても困らない。
