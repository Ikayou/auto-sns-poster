# auto-sns-poster

SNSへの動画を毎日自動生成・投稿するPythonプロジェクト。

## 概要

OpenAI APIを使って、バズる台本・背景画像・ナレーション音声を自動生成し、それらを合成して縦型ショート動画を作り、TikTok / Instagram Reels へ自動投稿する。

## アーキテクチャ

```
app/
  create_video.py         # 動画パイプライン（AI台本→画像→音声→動画合成）
  generate_assets.py      # 台本・画像の個別生成（テスト用）
  post_to_sns.py          # Instagram Reels への投稿
  get_token_direct.py     # TikTok OAuthトークン取得
  run_daily.py            # 毎朝7時に自動実行するスケジューラー
  fetch_content.py        # RSS/APIから記事を取得
  create_carousel.py      # カルーセルパイプライン（RSS→AI→Playwright→PNG）
  create_canva_carousel.py# Canvaパイプライン（RSS→AI→Canva API→PNG）★新
  canva_auth.py           # Canva Connect API OAuth認証ヘルパー ★新
  post_tiktok_carousel.py # TikTokフォトカルーセル投稿
templates/
  slide_title.html        # 1枚目：タイトルスライドテンプレート
  slide_content.html      # 2〜N枚目：コンテンツスライドテンプレート
  slide_cta.html          # 最終枚：フォロー誘導スライドテンプレート
assets/
  NotoSansJP-Bold.ttf     # 字幕用日本語フォント（必須）
  content.json            # 動画用AIコンテンツ（実行後に生成）
  carousel_content.json   # カルーセル用AIコンテンツ（実行後に生成）
output/
  reels.mp4               # 完成動画
  carousel/               # カルーセル用スライドPNG（slide_01.png〜）
```

## 実行方法

### Canvaでカルーセル画像を生成してTikTokへ投稿（Canvaパイプライン ★推奨）

```powershell
# 1. RSS取得 → AI生成 → assets/carousel_content.json に保存
python app/create_canva_carousel.py

# 2. Claude Code で Canva スライドを生成（PNG を output/carousel/ に保存）
#    → Claude Code のチャットで以下を入力:
/make-canva-slides

# 3. TikTokへカルーセル投稿
python app/post_tiktok_carousel.py
```

使用テンプレートID（Canva・選択済み）:
| スライド | デザインID | 編集URL |
|---|---|---|
| タイトル | DAHKwLcEEmA | https://www.canva.com/d/IEW4lxp3JdwxJ8p |
| コンテンツ | DAHKwGZP6uw | https://www.canva.com/d/5yKlqgiIFJQwyN- |
| CTA | DAHKwHaO_so | https://www.canva.com/d/j_lmDyPuHQvXZNz |

### Playwriteでカルーセル画像を生成してTikTokへ投稿（Playwright フォールバック）

```powershell
# 1. スライドPNGを生成（RSS→AI→Playwright）
python app/create_carousel.py

# 2. TikTokへカルーセル投稿
python app/post_tiktok_carousel.py
```

### 動画を1本生成する（従来パイプライン）

```powershell
python app/create_video.py
```

### 毎日自動実行するスケジューラーを起動

```powershell
python app/run_daily.py
```

### Dockerで動かす場合

```powershell
docker-compose up -d
docker-compose exec worker python app/create_carousel.py
```

## 環境変数（.env）

`.env.example` を参考に `.env` を作成する。**`.env` は絶対にGitにコミットしない。**

| キー | 説明 |
|------|------|
| `OPENAI_API_KEY` | OpenAI APIキー（台本・画像・音声生成に使用） |
| `TIKTOK_ACCESS_TOKEN` | TikTok投稿用アクセストークン |
| `CLIENT_KEY` / `CLIENT_SECRET` | TikTok OAuthアプリの認証情報 |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API トークン（未使用中） |
| `TIKTOK_ACCOUNT_NAME` | CTAスライドに表示するアカウント名（例: `your_tiktok`） |
| `CANVA_CLIENT_ID` | Canva Developer Portal のアプリ Client ID |
| `CANVA_CLIENT_SECRET` | Canva Developer Portal のアプリ Client Secret |
| `CANVA_TEMPLATE_TITLE` | Canva ブランドテンプレートID（タイトルスライド用） |
| `CANVA_TEMPLATE_CONTENT` | Canva ブランドテンプレートID（コンテンツスライド用） |
| `CANVA_TEMPLATE_CTA` | Canva ブランドテンプレートID（CTAスライド用） |

## 動画生成パイプライン（create_video.py）

1. `generate_daily_content()` — GPT-4o-miniでジャンルをランダム選択し、台本・画像プロンプト・キャプション・ハッシュタグをJSON生成
2. `generate_background_image()` — `gpt-image-1-mini` で縦型（1024x1536）背景画像を生成
3. `generate_audio()` — OpenAI TTS（voice: nova）でナレーション音声を生成
4. `add_text_to_image()` — Pillowでタイトル（ゴールド）とナレーション（白）を字幕として焼き込む
5. `create_ai_video()` — moviepyで画像＋音声を合成し MP4 として書き出す

## Canvaカルーセルパイプライン（create_canva_carousel.py）★推奨

1. `fetch_articles()` — 複数RSSフィードから記事を収集（NHK・はてな・TechCrunch・Gigazine）
2. `generate_carousel_content()` — GPT-4o-miniが最もバズりそな記事を選び、スライド構成(JSON)を生成
3. `create_slides_with_canva()` — Canva Connect API でブランドテンプレートへ自動入力し PNG をエクスポート
   - `_autofill()` — `POST /v1/autofills` でテキストフィールドを入力、完了をポーリング
   - `_export_png()` — `POST /v1/exports` で PNG をエクスポートし output/carousel/ に保存
4. `post_carousel()` — TikTok Content Posting API (v2) でフォトカルーセルとして投稿

## Playwriteカルーセルパイプライン（create_carousel.py）フォールバック

1. `fetch_articles()` — 複数RSSフィードから記事を収集（NHK・はてな・TechCrunch・Gigazine）
2. `generate_carousel_content()` — GPT-4o-miniが最もバズりそな記事を選び、スライド構成(JSON)を生成
3. `render_slides()` — HTMLテンプレートにデータを注入し、Playwrightで1080x1920のPNGとして書き出す
4. `post_carousel()` — TikTok Content Posting API (v2) でフォトカルーセルとして投稿

RSSフィードは `app/fetch_content.py` の `RSS_FEEDS` リストで自由に変更可能。

## 依存ライブラリ

```
openai        # AI生成（テキスト・画像・音声）
moviepy       # 動画合成
pillow        # 画像処理・字幕描画
python-dotenv
requests
feedparser    # RSS取得（カルーセルパイプラインで使用）
playwright    # HTML→PNG変換（カルーセルパイプラインで使用）
gTTS          # （現在未使用）
```

インストール:

```powershell
pip install -r requirements.txt

# Playwright は追加でブラウザのインストールが必要
playwright install chromium
```

## 注意事項

- `assets/NotoSansJP-Bold.ttf` が存在しないと字幕描画でエラーになる
- 生成された `assets/` と `output/` 以下のファイルはGitignore推奨
- Instagram投稿（`post_to_sns.py`）は公開アクセス可能な動画URLが必要
- TikTokアクセストークンは有効期限があるため、定期的に `get_token_direct.py` で更新が必要
