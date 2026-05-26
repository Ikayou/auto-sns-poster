# make-canva-slides

`assets/carousel_content.json` を読み込み、Canva MCP ツールを使って
カルーセルスライドを作成し `output/carousel/` に PNG として保存する。

## テンプレートID（固定）

| スライド種別 | Canva デザインID |
|---|---|
| タイトル（1枚目） | `DAHKwLcEEmA` |
| コンテンツ（2枚目〜） | `DAHKwGZP6uw` |
| CTA（最終枚） | `DAHKwHaO_so` |

## 実行手順

以下をすべて自動で行う：

1. `assets/carousel_content.json` を読み込む
2. **タイトルスライド**
   - `DAHKwLcEEmA` を `copy-design` でコピー
   - `start-editing-transaction` → `perform-editing-operations` でテキストを書き換え
     - タグ（tag）、タイトル（title）、サブタイトル（subtitle）
   - `commit-editing-transaction` → `export-design`（PNG）
   - `output/carousel/slide_01.png` に保存
3. **コンテンツスライド**（slides 配列の要素数だけ繰り返し）
   - `DAHKwGZP6uw` をコピー → テキスト書き換え（heading / body / index）
   - `output/carousel/slide_02.png`、`slide_03.png`…として保存
4. **CTAスライド**
   - `DAHKwHaO_so` をコピー → テキスト書き換え（cta_text / account_name）
   - 最後の番号の PNG として保存
5. 保存したファイル一覧を報告する

## 注意事項

- `output/carousel/` ディレクトリが存在しない場合は作成する
- PNG のダウンロードURLは `export-design` のレスポンスから取得し、`requests` で保存する
- エラーが出た場合は内容を報告して止める
