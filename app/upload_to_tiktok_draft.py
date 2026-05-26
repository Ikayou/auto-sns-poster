"""
Upload a generated video to TikTok's inbox editing flow.

This does not publish the video. TikTok sends an inbox notification to the
creator, who then opens the TikTok app, edits the video, adds music, and posts.

Run:
  python app/upload_to_tiktok_draft.py
"""

import json
import math
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
VIDEO_PATH = ROOT_DIR / "output" / "carousel_video.mp4"
CONTENT_PATH = ROOT_DIR / "assets" / "carousel_content.json"

ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
BASE_URL = "https://open.tiktokapis.com/v2"

MIN_CHUNK = 5 * 1024 * 1024
MAX_CHUNK = 64 * 1024 * 1024


def _calc_chunk_size(file_size: int) -> int:
    if file_size <= MIN_CHUNK:
        return file_size
    return min(MAX_CHUNK, max(MIN_CHUNK, file_size))


def init_draft_upload(video_path: Path) -> dict:
    file_size = video_path.stat().st_size
    chunk_size = _calc_chunk_size(file_size)
    total_chunks = math.ceil(file_size / chunk_size)

    print(f"   ファイルサイズ: {file_size / 1024 / 1024:.1f} MB")
    print(f"   チャンクサイズ: {chunk_size / 1024 / 1024:.1f} MB x {total_chunks} チャンク")

    url = f"{BASE_URL}/post/publish/inbox/video/init/"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        }
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    data = resp.json()
    print(f"   init レスポンス [{resp.status_code}]: {data}")

    if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
        raise RuntimeError(f"TikTok下書きアップロード初期化エラー: {data}")

    return data["data"]


def upload_video_chunks(upload_url: str, video_path: Path):
    file_size = video_path.stat().st_size
    chunk_size = _calc_chunk_size(file_size)
    total_chunks = math.ceil(file_size / chunk_size)

    with open(video_path, "rb") as f:
        for i in range(total_chunks):
            chunk_data = f.read(chunk_size)
            start_byte = i * chunk_size
            end_byte = min(start_byte + len(chunk_data) - 1, file_size - 1)

            headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
                "Content-Length": str(len(chunk_data)),
            }
            resp = requests.put(upload_url, data=chunk_data, headers=headers, timeout=300)
            if resp.status_code not in (200, 201, 206):
                raise RuntimeError(
                    f"チャンク{i + 1}アップロードエラー [{resp.status_code}]: {resp.text}"
                )
            print(f"  ✅ チャンク {i + 1}/{total_chunks} アップロード完了")


def check_upload_status(publish_id: str, timeout_sec: int = 180) -> str:
    url = f"{BASE_URL}/post/publish/status/fetch/"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.post(url, json={"publish_id": publish_id}, headers=headers, timeout=60)
        data = resp.json()
        status = data.get("data", {}).get("status", "PROCESSING")
        print(f"   ステータス: {status}")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            return status
        time.sleep(10)
    return "TIMEOUT"


def load_suggested_caption() -> str:
    if not CONTENT_PATH.exists():
        return ""

    with open(CONTENT_PATH, encoding="utf-8") as f:
        content = json.load(f)

    caption = content.get("caption", "")
    hashtags = " ".join(content.get("hashtags", []))
    return (caption + "\n\n" + hashtags).strip()


def upload_to_tiktok_draft(video_path: Path = VIDEO_PATH) -> str:
    if not ACCESS_TOKEN:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN が設定されていません")
    if not video_path.exists():
        raise FileNotFoundError(f"動画が見つかりません: {video_path}")

    print(f"🚀 TikTok下書き用アップロードを開始します: {video_path.name}")
    print("📋 [1/3] InboxアップロードURLを取得中...")
    init_data = init_draft_upload(video_path)
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]
    print(f"   publish_id: {publish_id}")

    print("📤 [2/3] 動画をTikTokへアップロード中...")
    upload_video_chunks(upload_url, video_path)

    print("⏳ [3/3] TikTokアプリへの通知状態を確認中...")
    status = check_upload_status(publish_id)

    if status == "SEND_TO_USER_INBOX":
        print("✅ TikTokアプリのInboxへ送信されました")
        suggested_caption = load_suggested_caption()
        if suggested_caption:
            print("\n--- 手動投稿用キャプション案 ---")
            print(suggested_caption)
            print("--- ここまで ---")
        print("\n次はTikTokアプリを開き、Inbox通知から動画を編集してください。")
        print("音楽を選び、AI生成ラベルをオンにしてから投稿してください。")
    elif status == "PUBLISH_COMPLETE":
        print("✅ TikTok側で投稿完了として扱われています")
    else:
        print(f"⚠️ ステータス: {status}")

    return publish_id


if __name__ == "__main__":
    upload_to_tiktok_draft()
