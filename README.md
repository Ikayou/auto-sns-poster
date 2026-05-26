# auto-sns-poster

heise.de の最新テックニュースをもとに、毎日 TikTok 用のニュース動画下書きを作るプロジェクトです。

現在の運用は次の流れです。

1. heise.de RSS からニュースを取得
2. OpenAI API でドイツ語の短いニュース構成を作成
3. HTML テンプレートから 7 枚の画像を生成
4. 7 枚の画像を 1 本の MP4 動画に変換
5. TikTok アプリの Inbox / 編集フローへ送信
6. スマホの TikTok アプリで音楽と AI 生成ラベルを設定して投稿

直接公開はしません。TikTok アプリ側で最後に確認して投稿します。

## 生成される内容

- `slide_01.png`: 表紙
- `slide_02.png` から `slide_06.png`: heise.de から選んだ 5 件のニュース
- `slide_07.png`: 終わりのページ
- `carousel_video.mp4`: 7 枚をつなげた TikTok 用動画

画像内の文字はドイツ語です。

## 主なファイル

```text
app/
  create_carousel.py          heise.de取得、AI生成、PNGスライド作成
  slides_to_video.py          PNGスライドをMP4動画へ変換
  upload_to_tiktok_draft.py   TikTokのInbox編集フローへ動画を送信
  print_tiktok_auth_url.py    TikTok認証URLを表示
  get_token_direct.py         認証codeをaccess tokenへ交換
  check_tiktok_info.py        tokenのTikTokアカウント確認

templates/
  heise_cover.html            表紙テンプレート
  single_news.html            ニュース本文テンプレート
  heise_outro.html            終わりのページテンプレート

assets/
  carousel_content.json       AIが作った投稿内容

output/
  carousel/                   生成されたPNGスライド
  carousel_video.mp4          生成された動画
```

## セットアップ

Python 環境で依存関係を入れます。

```bash
pip install -r requirements.txt
playwright install chromium
```

GitHub Actions でも使うため、GitHub Secrets にも同じキーを入れてください。

## .env

ローカル実行では `.env` が必要です。

```env
OPENAI_API_KEY=sk-...

CLIENT_KEY=...
CLIENT_SECRET=...
CODE=...
TIKTOK_ACCESS_TOKEN=...

TIKTOK_ACCOUNT_NAME=german.news69
TIKTOK_REDIRECT_URI=https://ikayou.github.io/tiktok-api-legal/
TIKTOK_SCOPES=user.info.basic,video.upload,video.publish

NEWS_COUNT=5
SECONDS_PER_SLIDE=8.0
```

注意: `TIKTOK_ACCOUNT_NAME` は画像内に表示する名前です。実際にどのTikTokアカウントへ下書きが届くかは `TIKTOK_ACCESS_TOKEN` の持ち主で決まります。

## TikTok認証

TikTok下書きを `german.news69` に送りたい場合は、ブラウザで普通のTikTokアカウント `german.news69` にログインした状態で認証します。

```bash
python app/print_tiktok_auth_url.py
```

表示されたURLを開いて許可します。戻ってきたURLに `code=...` が付くので、その値を `.env` の `CODE=` に入れます。

そのあとすぐに実行します。

```bash
python app/get_token_direct.py
```

表示された access token を `.env` の `TIKTOK_ACCESS_TOKEN=` に入れます。

確認します。

```bash
python app/check_tiktok_info.py
```

`creator_username` が `german.news69` なら、そのアカウントに下書きが届きます。

GitHub Actions で毎朝動かす場合は、GitHub Secrets の `TIKTOK_ACCESS_TOKEN` も新しい token に更新してください。

## 手動実行

ローカルで1回作るときはこの順番です。

```bash
python app/create_carousel.py
python app/slides_to_video.py
python app/upload_to_tiktok_draft.py
```

成功すると TikTok アプリに通知が届きます。スマホで TikTok を開き、Inbox から動画を編集して、音楽を選び、AI生成ラベルをオンにして投稿します。

## 自動実行

`.github/workflows/daily_post.yml` で毎日実行します。

現在のスケジュール:

```text
05:00 UTC
```

ドイツ夏時間では朝 7:00、冬時間では朝 6:00 です。

GitHub の Actions 画面から `workflow_dispatch` で手動実行もできます。

## GitHub Secrets

GitHub Actions には最低限これを設定します。

```text
OPENAI_API_KEY
TIKTOK_ACCESS_TOKEN
TIKTOK_ACCOUNT_NAME
```

`TIKTOK_ACCOUNT_NAME` は `german.news69` にしてください。

## 現在のTikTok投稿方式

現在は動画ファイルを `FILE_UPLOAD` で TikTok に送る方式です。

この方式では GitHub Pages の画像URL認証は使いません。写真カルーセルをURLから読み込ませる方式では URL ownership verification が必要ですが、申請が通るまでは通常運用では使いません。

## 出力ファイル

生成物は Git 管理しません。

```text
assets/*
output/*
```

ただし `.gitkeep` は残します。

## よく使う確認コマンド

```bash
python app/check_tiktok_info.py
```

TikTok token がどのアカウントに紐づいているか確認します。

```bash
python app/create_carousel.py
```

heise.de からニュースを取り、7枚の画像を作ります。

```bash
python app/slides_to_video.py
```

画像を1本の動画にします。

```bash
python app/upload_to_tiktok_draft.py
```

動画をTikTokアプリの編集フローへ送ります。

## 注意

- `.env` は絶対に Git に入れないでください。
- `CODE` は一度しか使えません。期限も短いので、認証後すぐに `get_token_direct.py` を実行してください。
- TikTokで音楽を選ぶことと、AI生成ラベルをオンにすることは、スマホアプリ側で手動で行います。
- 下書きが違うアカウントへ届く場合は、token を作ったときにログインしていたTikTokアカウントが違います。
