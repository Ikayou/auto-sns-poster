# 軽量で安定している slim バージョンを使用
FROM python:3.11-slim

# MoviePyを動かすための必須パッケージ（ffmpeg）をインストール
# キャッシュを削除してイメージサイズを軽量化するベストプラクティス
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# ライブラリのリストをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ※ソースコード(appディレクトリ等)はdocker-composeのvolumesでマウントするため、ここではCOPYしません