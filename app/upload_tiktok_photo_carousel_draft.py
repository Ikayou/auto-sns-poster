"""
Upload PNG slides as a TikTok photo carousel for the app editing flow.

This does not directly publish. TikTok sends an inbox notification, and the
creator completes the post in the TikTok app, where music can be selected.

Run:
  python app/upload_tiktok_photo_carousel_draft.py
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.post_tiktok_carousel import push_to_github_pages

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
CAROUSEL_DIR = ROOT_DIR / "output" / "carousel"
CONTENT_PATH = ROOT_DIR / "assets" / "carousel_content.json"

ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
BASE_URL = "https://open.tiktokapis.com/v2"
PHOTO_TITLE_LIMIT = 90
PHOTO_DESCRIPTION_LIMIT = 4000


def create_photo_carousel_draft(photo_urls: list[str], caption: str, hashtags: list[str]) -> str:
    full_caption = (caption + "\n\n" + " ".join(hashtags)).strip()
    payload = {
        "post_info": {
            "title": (caption or "heise.de Top 5")[:PHOTO_TITLE_LIMIT],
            "description": full_caption[:PHOTO_DESCRIPTION_LIMIT],
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_images": photo_urls,
            "photo_cover_index": 0,
        },
        "media_type": "PHOTO",
        "post_mode": "MEDIA_UPLOAD",
    }

    print("   投稿モード: MEDIA_UPLOAD / 写真カルーセル")
    print(f"   画像枚数: {len(photo_urls)}")
    resp = requests.post(
        f"{BASE_URL}/post/publish/content/init/",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json=payload,
        timeout=60,
    )
    data = resp.json()
    print(f"   APIレスポンス [{resp.status_code}]: {data}")

    if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
        raise RuntimeError(f"TikTok写真カルーセル下書き送信エラー: {data}")

    return data["data"]["publish_id"]


def check_publish_status(publish_id: str, timeout_sec: int = 180) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.post(
            f"{BASE_URL}/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        data = resp.json()
        status = data.get("data", {}).get("status", "PROCESSING")
        print(f"   ステータス: {status}")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            return status
        time.sleep(10)
    return "TIMEOUT"


def load_content() -> tuple[str, list[str]]:
    if not CONTENT_PATH.exists():
        return "heise.deの最新テックニュースをまとめました。どれが気になりますか？", [
            "#テックニュース",
            "#heise",
            "#IT",
        ]

    with open(CONTENT_PATH, encoding="utf-8") as f:
        content = json.load(f)
    return content.get("caption", ""), content.get("hashtags", [])


def upload_photo_carousel_draft() -> str:
    if not ACCESS_TOKEN:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN が設定されていません")

    image_paths = sorted(CAROUSEL_DIR.glob("slide_*.png"))
    if not image_paths:
        raise FileNotFoundError(f"スライド画像が見つかりません: {CAROUSEL_DIR}")

    caption, hashtags = load_content()
    print(f"🚀 TikTok写真カルーセル下書き送信を開始します（{len(image_paths)}枚）")

    print("\n📤 [1/3] GitHub Pagesへ画像を公開中...")
    photo_urls = push_to_github_pages(image_paths)

    print("\n📋 [2/3] TikTok Inbox編集フローへ送信中...")
    publish_id = create_photo_carousel_draft(photo_urls, caption, hashtags)
    print(f"   publish_id: {publish_id}")

    print("\n⏳ [3/3] 送信ステータスを確認中...")
    status = check_publish_status(publish_id)
    print(f"   最終ステータス: {status}")

    if status == "SEND_TO_USER_INBOX":
        print("\n✅ TikTokアプリのInboxへ送信されました")
        print("   TikTokアプリを開いて、音楽を選んで投稿してください。")
    elif status == "PUBLISH_COMPLETE":
        print("\n✅ TikTok側で完了として扱われています")
    else:
        print("\n⚠️ TikTokアプリ側で状態を確認してください")

    return publish_id


if __name__ == "__main__":
    upload_photo_carousel_draft()
