# 台本

漫才の台本を置くところ。1 本につき 2 つのファイルがある。

- `<題材>.md` … **読む用**。役名・間・叩くツッコミ・声の変わり目を言葉で書いたもの（`.txt` から自動で作る。直接は直さない）
- `<題材>.txt` … **音声と動画を作る元**。直すのはこちら（書き方は `proto/hacker.txt` の頭、決まりごとは `docs/SCRIPT_GUIDE.md`）

| 台本 | 題名 | お題 | コンビ | 長さ（VOICEVOX） |
|---|---|---|---|---|
| [chappy2](chappy2.md) | AIがうつった男 | AI構文（チャッピー構文）の作り直し | 男性 | 2分48秒 |
| [dopagaki](dopagaki.md) | 退屈できない男 | ドパガキ | 男性 | 2分48秒 |
| [maratan](maratan.md) | マーラータンに量られた女 | 麻辣湯（マーラータン） | 女性 | 2分51秒 |

前に作った台本（ハッカー、インフルエンサー、最初のチャッピー構文）は `proto/` にある。

## 作り方

```bash
python proto/synth.py scripts/<題材>.txt --backend voicevox   # 声（VOICEVOX を起動しておく）
python proto/vv_kana.py scripts/<題材>.txt                    # 読みをカナで確かめる（build/kana/）
python proto/script_md.py scripts/<題材>.txt                  # 読む用の .md を作り直す
```
