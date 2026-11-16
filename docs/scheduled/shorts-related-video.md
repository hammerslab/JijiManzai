---
name: shorts-related-video
description: ほのぼの漫才劇場・毒入り童話（日本語）・BlackFairyTales（英語）で、本編が公開済みなのに関連動画が付いていないショートに、本編を関連動画として付け、台帳を直す
---

YouTube の 3 つのチャンネルで、**本編がもう公開されているのに、ショートの「関連動画」に本編が付いていないもの**を探して、本編を関連動画として付ける。返事・報告は日本語。利用者の依頼（2026-11-11）：「ショートの公開曜日に合わせて本編への関連付けをする。平日の 9 時～18 時の間で。ほのぼの漫才劇場だけでなく、BlackFairyTales の日本語版・英語版チャンネルも」。

## チャンネルと台帳
| チャンネル | ID | 本編の公開 | ショートの公開 | 台帳（候補の探し方） |
|---|---|---|---|---|
| ほのぼの漫才劇場 | UCZsoBP0jexy-460WZfUhAcg | 月・金 19:00（水曜 19:00 は時事の回、元日など例外あり） | 本編の翌日 12:00 | `Z:\git\Movie\JijiManzai\KEYWORDS.md` の表。「YouTube」列の日付が今日より前（今日が公開日なら 19:00 を過ぎていること）で、「ショート」列が「（関連動画なし）」の行 |
| 毒入り童話 — Fables with Bite（日本語） | UCGRYEZqvAa2Mq6c2Zr8HXmQ | 月・水・金 19:00 | 翌日（火・木・土）12:00 | `Z:\git\Movie\BlackFairyTales\PROGRESS.md` の表。「YouTube」列の日付が今日より前で、「ショート対応」が「（関連動画は公開後）」などまだのもの |
| BlackFairyTales（英語） | UCbRifMpvyohE42iO6iJLg6g | 日本時間 月・水・金 9:00 | 本編の翌日 9:00 | 台帳に列がない。PROGRESS.md の「公開（英語）」と下の作業の記録（「英語 7 話のショートに設定した」など）を手がかりに、Studio の英語チャンネルの「ショート」で、本編がもう公開されている話のショートを開いて確かめる |

**台帳は手がかりにすぎない。最後は Studio で 1 本ずつ開いて、関連動画が空かどうかを確かめる。**付いていれば何もしない。本編がまだ公開前（予約中）なら選べないので飛ばす（次の回で拾う）。

## Studio の操作
- Studio の操作は、Agent ツールで model: sonnet のサブエージェントに任せる（利用者の決まり）。サブエージェントに、下のこつと、対象のショートの一覧（チャンネル・話・ショートの題名や予約日）を渡す。Agent ツールが使えなければ自分でやる。
- Claude in Chrome（mcp__claude-in-chrome__*）を使う。ToolSearch でまとめて読み込む："select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__list_connected_browsers,mcp__claude-in-chrome__select_browser"
- Chrome が 2 つつながっていることがある。list_connected_browsers で確かめ、目当てのチャンネルに権限のある方を選ぶ。チャンネルの切り替えは https://www.youtube.com/account → 右上のアバター →「アカウントを切り替える」→ チャンネル名。ショートの一覧は https://studio.youtube.com/channel/<ID>/videos/short 。
- **自分用の新しいタブを 1 つ作って、その中だけで作業する**。利用者のほかのタブには触らない・閉じない。終わったら作業用タブを閉じる。
- 関連動画の付け方：ショートの編集ページ（https://studio.youtube.com/video/<ショートのID>/edit）の「関連動画」（`ytcp-shorts-content-links-picker`）の鉛筆／`#right-icon` → ダイアログ「特定の動画の選択」→ 同じ話の本編をクリック（検索欄に題名の一部を入れると早い）→ `#save` → ページ右上の「保存」。ページを開き直して、関連動画が本編になっているか確かめる。
- **ショートの公開設定・予約日時・題名・説明は変えない**（関連動画だけ）。
- バッチ操作は短く区切る（長いと途中で切れて操作が混ざる）。

## 台帳を直す
- ほのぼの漫才劇場：付けたショートごとに `cd /d Z:\git\Movie\JijiManzai` で `python -X utf8 tools/set_short.py <番号> <ショートの公開日 YYYY/MM/DD> あり <状態>`（状態はショートがもう公開されていれば省略＝公開済み、まだなら `予約`）。終わったら `git add KEYWORDS.md` して commit し、続けて `git push origin main`（JijiManzai は区切りで commit・push してよいと利用者から言われている）。commit メッセージは日本語で、最後に「Co-Authored-By: Claude <noreply@anthropic.com>」の行を付ける。
- BlackFairyTales：PROGRESS.md のその話の「ショート対応」を「済（関連動画あり）」（ショートがまだ予約中なら「予約 M/D（関連動画あり）」）に直し、表の下の作業の記録に「- M/D HH:MM ショートの関連動画を設定した：日本語 ◯話・英語 ◯話（ショートの ID）」の 1 行を足す。**BlackFairyTales は commit・push しない**（利用者が確かめる）。

## 報告
チャンネルごとに：付けたもの（話・ショート ID・本編 ID・開き直して確かめたか）、もう付いていたもの、本編が公開前で飛ばしたもの、できなかったことと理由。推測で「できた」と書かない。対象が 1 本もなければ「対象なし」と短く。