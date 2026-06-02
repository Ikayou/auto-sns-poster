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
from tiktok_token import get_access_token

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
VIDEO_PATH = ROOT_DIR / "output" / "carousel_video.mp4"
CONTENT_PATH = ROOT_DIR / "assets" / "carousel_content.json"
BASE_URL = "https://open.tiktokapis.com/v2"

MIN_CHUNK = 5 * 1024 * 1024
MAX_CHUNK = 64 * 1024 * 1024
STATUS_TIMEOUT_SEC = int(os.getenv("TIKTOK_UPLOAD_STATUS_TIMEOUT_SEC", "900"))
STATUS_POLL_INTERVAL_SEC = int(os.getenv("TIKTOK_UPLOAD_STATUS_POLL_INTERVAL_SEC", "10"))
UPLOAD_SUCCESS_STATUSES = (200, 201, 206)


def _calc_chunk_size(file_size: int) -> int:
    if file_size <= MIN_CHUNK:
        return file_size
    return min(MAX_CHUNK, max(MIN_CHUNK, file_size))


def init_draft_upload(video_path: Path, access_token: str) -> dict:
    file_size = video_path.stat().st_size
    chunk_size = _calc_chunk_size(file_size)
    total_chunks = math.ceil(file_size / chunk_size)

    print(f"   ファイルサイズ: {file_size / 1024 / 1024:.1f} MB")
    print(f"   チャンクサイズ: {chunk_size / 1024 / 1024:.1f} MB x {total_chunks} チャンク")

    url = f"{BASE_URL}/post/publish/inbox/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
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
        error_code = data.get("error", {}).get("code")
        if error_code == "access_token_invalid":
            raise RuntimeError(
                "TikTok access token is invalid. Update the GitHub Secret "
                "TIKTOK_REFRESH_TOKEN, then let the workflow refresh the "
                "access token automatically."
            )
        if error_code == "scope_not_authorized":
            raise RuntimeError(
                "TikTok token does not have the video.upload scope. Re-run OAuth "
                "with TIKTOK_SCOPES including video.upload, then update "
                "TIKTOK_REFRESH_TOKEN in GitHub Secrets."
            )
        if error_code == "spam_risk_too_many_pending_share":
            raise RuntimeError(
                "TikTok rejected the upload because too many API uploads are still "
                "pending in the creator Inbox. Open the TikTok app, handle or clear "
                "the pending Inbox uploads, then run the workflow again."
            )
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
            uploaded_range = resp.headers.get("Content-Range")
            range_note = f", Content-Range: {uploaded_range}" if uploaded_range else ""
            print(
                f"  TikTok upload response [{resp.status_code}] "
                f"chunk {i + 1}/{total_chunks}{range_note}"
            )

            if resp.status_code not in UPLOAD_SUCCESS_STATUSES:
                raise RuntimeError(
                    f"チャンク{i + 1}アップロードエラー [{resp.status_code}]: {resp.text}"
                )
            print(f"  ✅ チャンク {i + 1}/{total_chunks} アップロード完了")


def check_upload_status(
    publish_id: str, access_token: str, timeout_sec: int = STATUS_TIMEOUT_SEC
) -> dict:
    url = f"{BASE_URL}/post/publish/status/fetch/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    deadline = time.time() + timeout_sec
    last_status_data = {"status": "PROCESSING"}
    while time.time() < deadline:
        resp = requests.post(url, json={"publish_id": publish_id}, headers=headers, timeout=60)
        data = resp.json()
        if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
            raise RuntimeError(f"TikTokステータス取得エラー [{resp.status_code}]: {data}")

        status_data = data.get("data") or {}
        status = status_data.get("status", "PROCESSING")
        last_status_data = status_data

        details = []
        if "uploaded_bytes" in status_data:
            details.append(f"uploaded_bytes={status_data['uploaded_bytes']}")
        if status_data.get("fail_reason"):
            details.append(f"fail_reason={status_data['fail_reason']}")
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"   ステータス: {status}{suffix}")

        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            return status_data
        time.sleep(STATUS_POLL_INTERVAL_SEC)

    last_status_data["status"] = "TIMEOUT"
    return last_status_data


def load_suggested_caption() -> str:
    if not CONTENT_PATH.exists():
        return ""

    with open(CONTENT_PATH, encoding="utf-8") as f:
        content = json.load(f)

    caption = content.get("caption", "")
    hashtags = " ".join(content.get("hashtags", []))
    return (caption + "\n\n" + hashtags).strip()


def upload_to_tiktok_draft(video_path: Path = VIDEO_PATH) -> str:
    if not video_path.exists():
        raise FileNotFoundError(f"動画が見つかりません: {video_path}")

    access_token = get_access_token()

    print(f"🚀 TikTok下書き用アップロードを開始します: {video_path.name}")
    print("📋 [1/3] InboxアップロードURLを取得中...")
    init_data = init_draft_upload(video_path, access_token)
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]
    print(f"   publish_id: {publish_id}")

    print("📤 [2/3] 動画をTikTokへアップロード中...")
    upload_video_chunks(upload_url, video_path)

    print("⏳ [3/3] TikTokアプリへの通知状態を確認中...")
    status_data = check_upload_status(publish_id, access_token)
    status = status_data.get("status", "UNKNOWN")

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
    elif status == "FAILED":
        raise RuntimeError(f"TikTok下書きアップロードに失敗しました: {status_data}")
    else:
        raise TimeoutError(
            "TikTokアプリのInboxへ送信されたことを確認できませんでした。"
            f"最終ステータス: {status_data}"
        )

    return publish_id


if __name__ == "__main__":
    upload_to_tiktok_draft()
