"""
TikTok 動画投稿（Content Posting API v2）

FILE_UPLOAD 方式:
  1. /v2/post/publish/video/init/  → チャンクアップロードURLを取得
  2. 動画をチャンク分割してPUT
  3. /v2/post/publish/status/fetch/ でステータス確認

実行:
  python app/post_to_tiktok_video.py
"""

import os
import json
import time
import math
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN  = os.getenv("TIKTOK_ACCESS_TOKEN", "")
BASE_URL      = "https://open.tiktokapis.com/v2"
PRIVACY_LEVEL = "SELF_ONLY"   # テスト中は SELF_ONLY、本番は FOLLOWER_OF_CREATOR

MIN_CHUNK  = 5  * 1024 * 1024  # 5MB  (TikTok下限)
MAX_CHUNK  = 64 * 1024 * 1024  # 64MB (TikTok上限)


def _calc_chunk_size(file_size: int) -> int:
    """TikTok の chunk_size ルール: 5MB〜64MB（最終チャンクのみ例外）"""
    if file_size <= MIN_CHUNK:
        return file_size  # 1チャンク＝最終チャンクなのでサイズ制限なし
    return min(MAX_CHUNK, max(MIN_CHUNK, file_size))


def init_video_upload(video_path: Path, caption: str, hashtags: list[str]) -> dict:
    full_caption = caption + "\n\n" + " ".join(hashtags)
    file_size    = video_path.stat().st_size
    chunk_size   = _calc_chunk_size(file_size)
    total_chunks = math.ceil(file_size / chunk_size)

    print(f"   ファイルサイズ: {file_size / 1024 / 1024:.1f} MB")
    print(f"   チャンクサイズ: {chunk_size / 1024 / 1024:.1f} MB × {total_chunks} チャンク")

    url     = f"{BASE_URL}/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type":  "application/json; charset=UTF-8",
    }
    payload = {
        "post_info": {
            "title":           full_caption[:2200],
            "privacy_level":   PRIVACY_LEVEL,
            "disable_comment": False,
        },
        "source_info": {
            "source":            "FILE_UPLOAD",
            "video_size":        file_size,
            "chunk_size":        chunk_size,
            "total_chunk_count": total_chunks,
        },
    }

    resp = requests.post(url, json=payload, headers=headers)
    data = resp.json()
    print(f"   init レスポンス [{resp.status_code}]: {data}")

    if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
        raise Exception(f"動画アップロード初期化エラー: {data}")

    return data["data"]


def upload_video_chunks(upload_url: str, video_path: Path):
    file_size    = video_path.stat().st_size
    chunk_size   = _calc_chunk_size(file_size)
    total_chunks = math.ceil(file_size / chunk_size)

    with open(video_path, "rb") as f:
        for i in range(total_chunks):
            chunk_data  = f.read(chunk_size)
            start_byte  = i * chunk_size
            end_byte    = min(start_byte + len(chunk_data) - 1, file_size - 1)

            headers = {
                "Content-Type":  "video/mp4",
                "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
                "Content-Length": str(len(chunk_data)),
            }
            resp = requests.put(upload_url, data=chunk_data, headers=headers)
            if resp.status_code not in (200, 201, 206):
                raise Exception(f"チャンク{i+1}アップロードエラー [{resp.status_code}]: {resp.text}")
            print(f"  ✅ チャンク {i+1}/{total_chunks} アップロード完了")


def check_publish_status(publish_id: str, timeout_sec: int = 180) -> str:
    url     = f"{BASE_URL}/post/publish/status/fetch/"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}",
               "Content-Type": "application/json; charset=UTF-8"}

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp   = requests.post(url, json={"publish_id": publish_id}, headers=headers)
        data   = resp.json()
        status = data.get("data", {}).get("status", "PROCESSING")
        print(f"   ステータス: {status}")
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            return status
        time.sleep(10)
    return "TIMEOUT"


def post_video(video_path: Path, caption: str, hashtags: list[str]):
    print(f"🚀 TikTok動画投稿を開始します: {video_path.name}")

    print("📋 [1/3] アップロードURLを取得中...")
    init_data   = init_video_upload(video_path, caption, hashtags)
    publish_id  = init_data["publish_id"]
    upload_url  = init_data["upload_url"]
    print(f"   publish_id: {publish_id}")

    print("📤 [2/3] 動画をアップロード中...")
    upload_video_chunks(upload_url, video_path)

    print("⏳ [3/3] 投稿ステータスを確認中...")
    status = check_publish_status(publish_id)

    if status == "PUBLISH_COMPLETE":
        print(f"🎉 TikTokへの投稿が完了しました！ publish_id: {publish_id}")
    else:
        print(f"⚠️  ステータス: {status}（TikTokアプリで確認してください）")

    return publish_id


if __name__ == "__main__":
    video_path = Path("output/carousel_video.mp4")
    if not video_path.exists():
        print("❌ output/carousel_video.mp4 が見つかりません")
        print("   先に: python app/slides_to_video.py を実行してください")
        raise SystemExit(1)

    content_path = Path("assets/carousel_content.json")
    if not content_path.exists():
        print("❌ assets/carousel_content.json が見つかりません")
        raise SystemExit(1)

    with open(content_path, encoding="utf-8") as f:
        content = json.load(f)

    post_video(video_path, content["caption"], content["hashtags"])
