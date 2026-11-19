# Studio の作業を Sonnet に頼むときの頼みごと（ひな形）

> 2026-11-11 に 62 本の予約で使ったもの。日付・一覧のファイル名（`build/work/studio_upload_<日付>.json`）・担当の範囲は、そのつど書き換える。下の本文をそのまま Sonnet の Agent に渡す（「`docs/briefs/studio.md` を読んで、担当は〇〇」と頼む）。

YouTube Studio で、チャンネル「ほのぼの漫才劇場」（チャンネル ID UCZsoBP0jexy-460WZfUhAcg）に利用者がアップロードした下書きに、情報を入れて予約する。返事は日本語。

## 一覧
`Z:\git\Movie\JijiManzai\build\work\studio_upload_1111.json`（62 件。本編と、そのショートが交互に並ぶ）。各件は、ファイル名 file、種類 kind（main／short）、入れる値のファイル meta（`Z:\git\Movie\JijiManzai\` からの相対パス。■ タイトル／■ 説明／■ タグ／■ 再生リスト の見出しの下に値がある）、予約日時 schedule。**自分の担当の範囲（頼みごとに書いた件）だけ**やる。

1. Studio の「コンテンツ」（動画タブとショートタブ。ショートは読み込み直さないと出ないことがある。「下書き」で絞り込むと探しやすい）で、担当の件の下書きを探す。下書きの題名は、ふつうファイル名（例 0085_selfregi、0085 selfregi）。見つけたら JSON の id に動画 ID、uploaded を true。
2. 処理が終わっている下書きの編集画面で：
   - 題名・説明・タグ：meta のファイルの値をそのまま。説明は「■ 説明」の下の全部（ハッシュタグ行と「音声：…」の行も含む）。ショートにはタグの項目がないので空でよい。
   - サムネイル（本編だけ）：thumbs の 1 枚目（thumbnail_1.png）。mcp__claude-in-chrome__file_upload で、パスは `Z:\git\Movie\JijiManzai\` を前に付けた絶対パス。
   - 再生リスト：本編だけ、meta の「■ 再生リスト」の名前のリストに入れる（4 つとももうある）。**ショートは入れない**。
   - 設定：子ども向けではない、18 歳制限なし、カテゴリ＝コメディ、動画の言語＝日本語、有料プロモーション＝いいえ、「AI の使用（改変・合成コンテンツ）」＝いいえ。字幕は上げない。
   - **ショートの関連動画は付けない**（本編が公開前で選べない）。
   - 公開設定：「スケジュールを設定」で schedule の日時（日本時間）に予約。
   - 保存の直後に「スケジュールされた動画」の表示で日時を確かめ、ページを開き直して題名・説明が入っているかも確かめる。確かめたら done を true。
3. JSON は 1 件ごとに更新して保存する（ほかの件の行は書き換えない）。

## 操作のこつ（前回うまくいった方法）
- ⚠ **Studio の Agent は 1 人ずつ（直列）で動かす**。2026-11-19 に 5 人を同時に動かしたら、つながっている 2 つの Chrome の選択とタブのグループを取り合って、権限のないほうのブラウザで「このページを表示する権限がありません」になった。担当を分けるときも、前の人が終わってから次を頼む
- Chrome は 2 つつながっていて、片方は Lab Hammers のアカウント（Studio が「権限がありません」になる）。「Browser 1／2」の名前は呼ぶたびに入れ替わることがあるので、名前ではなく、Studio のコンテンツ画面が開けるかで選ぶ（2026-11-19 は deviceId 308095a1… のほう）
- 編集画面の再生リストの並びは、最近使ったものが先頭に来て毎回変わる。チェックを入れる前に名前を目で確かめる
- ショートタブの下書きは、絞り込みなしだと 0 件に見えることがある。「公開設定：ドラフト」で絞ると出る（2026-11-19、これで 8 本を見落とした）。下書きのショートは、ダイアログで入れて保存・予約するまで編集ページが開かない
- 保存中に「次へ」「スケジュールを設定」を押すと、押した位置の入力欄（説明など）に「19:00」「12:00」が混ざる。保存が終わるのを待つ。ダイアログのボタンの位置は画面の高さで変わるので、座標で押す前にスクリーンショットで確かめる
- ショートの題名に「#shorts」を打つとハッシュタグの候補が出て、説明の文字が題名に入ることがある。説明を先に入れてから題名を打つ
- 一覧の JSON は 1 件ごとに id・uploaded・done を書き換える（書き換え忘れた担当がいた）
- Claude in Chrome（mcp__claude-in-chrome__*）。ToolSearch でまとめて読み込む："select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__list_connected_browsers,mcp__claude-in-chrome__select_browser,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__form_input,mcp__claude-in-chrome__javascript_tool"
- Chrome が 2 つつながっていることがある。list_connected_browsers で確かめ、「ほのぼの漫才劇場」に権限のある方を選ぶ。権限がないと出たら https://www.youtube.com/account → 右上のアバター →「アカウントを切り替える」→「ほのぼの漫才劇場」。
- **自分用の新しいタブを 1 つ作って、その中だけで作業する**。ほかのタブには触らない・閉じない。
- 編集ページは https://studio.youtube.com/video/<ID>/edit 。
- 題名・説明は contenteditable。全選択（ctrl+a）してから computer の type。**保存が終わってから次の操作へ進む**（前回、保存の前に予約に進んで、説明に「19:00」が入ったことがある）。入れたあと get_page_text で確かめる。
- 日付：予約の日付欄をクリック → ポップアップの中の入力欄を選び直す → 全選択して「2027/06/14」のように type → Return。時刻欄も「19:00」「12:00」。JS で値を入れても反映されない。確定は「完了」（`#done-button` か `#save-button`）、そのあと右上の「保存」。
- バッチ操作は短く区切る。
- 終わったら作業用タブを閉じる。

## 報告
担当の件ごとに 1 行（番号・本編／ショート・動画 ID・予約日時・確かめた表示）、見つからなかった下書き、できなかったことと理由。推測で「できた」と書かないこと。
