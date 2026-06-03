"""
Publish generated PNG slides as an Instagram carousel.

Instagram carousel publishing uses public media URLs:
  1. Push local PNG slides to GitHub Pages
  2. Create one child media container per image URL
  3. Create a parent CAROUSEL container with those child IDs
  4. Publish the parent container

Run:
  python app/post_to_instagram_carousel.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.post_tiktok_carousel import push_to_github_pages

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
CAROUSEL_DIR = ROOT_DIR / "output" / "carousel"
CONTENT_PATH = ROOT_DIR / "assets" / "carousel_content.json"

API_VERSION = os.getenv("INSTAGRAM_API_VERSION") or "v24.0"
GRAPH_HOST = os.getenv("INSTAGRAM_GRAPH_HOST") or "graph.facebook.com"
BASE_URL = os.getenv("INSTAGRAM_GRAPH_BASE_URL") or f"https://{GRAPH_HOST}/{API_VERSION}"

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("INSTAGRAM_USER_ID") or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
PROCESSING_TIMEOUT_SEC = int(os.getenv("INSTAGRAM_PROCESSING_TIMEOUT_SEC", "900"))
PROCESSING_POLL_INTERVAL_SEC = int(os.getenv("INSTAGRAM_PROCESSING_POLL_INTERVAL_SEC", "10"))
CAPTION_LIMIT = 2200
MAX_CAROUSEL_ITEMS = int(os.getenv("INSTAGRAM_MAX_CAROUSEL_ITEMS", "10"))


def _require_settings():
    missing = []
    if not ACCESS_TOKEN:
        missing.append("INSTAGRAM_ACCESS_TOKEN")
    if not IG_USER_ID:
        missing.append("INSTAGRAM_USER_ID or INSTAGRAM_BUSINESS_ACCOUNT_ID")
    if missing:
        raise RuntimeError(f"Missing Instagram setting(s): {', '.join(missing)}")


def _decode_json_response(response: requests.Response, action: str) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Instagram {action} response was not JSON [{response.status_code}]: "
            f"{response.text}"
        ) from exc

    if response.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram {action} failed [{response.status_code}]: {data}")

    return data


def _full_caption(content: dict[str, Any] | None = None) -> str:
    if content is None:
        if not CONTENT_PATH.exists():
            return ""
        with open(CONTENT_PATH, encoding="utf-8") as f:
            content = json.load(f)

    caption = str(content.get("caption") or "").strip()
    hashtags = content.get("hashtags") or []
    hashtag_text = " ".join(str(tag).strip() for tag in hashtags if str(tag).strip())
    return (caption + "\n\n" + hashtag_text).strip()[:CAPTION_LIMIT]


def wait_for_container(container_id: str) -> dict[str, Any]:
    deadline = time.time() + PROCESSING_TIMEOUT_SEC
    last_data: dict[str, Any] = {"status_code": "IN_PROGRESS"}

    while time.time() < deadline:
        response = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
            timeout=60,
        )
        data = _decode_json_response(response, "status fetch")
        status_code = data.get("status_code", "IN_PROGRESS")
        last_data = data
        print(f"   container {container_id} status_code: {status_code}")

        if status_code == "FINISHED":
            return data
        if status_code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container processing failed: {data}")
        time.sleep(PROCESSING_POLL_INTERVAL_SEC)

    last_data["status_code"] = "TIMEOUT"
    raise TimeoutError(f"Instagram container processing timed out: {last_data}")


def create_image_container(
    image_url: str, *, carousel_item: bool, caption: str | None = None
) -> str:
    _require_settings()
    payload = {
        "image_url": image_url,
        "access_token": ACCESS_TOKEN,
    }
    if carousel_item:
        payload["is_carousel_item"] = "true"
    elif caption:
        payload["caption"] = caption

    response = requests.post(f"{BASE_URL}/{IG_USER_ID}/media", data=payload, timeout=60)
    data = _decode_json_response(response, "image container creation")

    container_id = data.get("id")
    if not container_id:
        raise RuntimeError(f"Instagram image container creation did not return an id: {data}")
    return container_id


def create_carousel_container(child_container_ids: list[str], caption: str) -> str:
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(child_container_ids),
        "caption": caption,
        "access_token": ACCESS_TOKEN,
    }

    response = requests.post(f"{BASE_URL}/{IG_USER_ID}/media", data=payload, timeout=60)
    data = _decode_json_response(response, "carousel container creation")

    container_id = data.get("id")
    if not container_id:
        raise RuntimeError(f"Instagram carousel container creation did not return an id: {data}")
    return container_id


def publish_container(container_id: str) -> str:
    response = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN},
        timeout=60,
    )
    data = _decode_json_response(response, "media publish")

    media_id = data.get("id")
    if not media_id:
        raise RuntimeError(f"Instagram media publish did not return an id: {data}")
    return media_id


def post_instagram_carousel(
    image_paths: list[Path] | None = None,
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paths = image_paths or sorted(CAROUSEL_DIR.glob("slide_*.png"))
    if not paths:
        raise FileNotFoundError(f"スライド画像が見つかりません: {CAROUSEL_DIR}")

    paths = paths[:MAX_CAROUSEL_ITEMS]
    caption = _full_caption(content)

    print(f"🚀 Instagram画像投稿を開始します（{len(paths)}枚）")
    print("📤 [Instagram 1/4] GitHub Pagesへ画像を公開中...")
    image_urls = push_to_github_pages(paths)

    if len(image_urls) == 1:
        print("📋 [Instagram 2/4] 単独画像コンテナを作成中...")
        container_id = create_image_container(
            image_urls[0], carousel_item=False, caption=caption
        )
        print("⏳ [Instagram 3/4] 画像処理を待機中...")
        status_data = wait_for_container(container_id)
        print("📢 [Instagram 4/4] 画像投稿を公開中...")
        media_id = publish_container(container_id)
        print(f"🎉 Instagram画像投稿完了: {media_id}")
        return {
            "mode": "single_image",
            "container_id": container_id,
            "child_container_ids": [],
            "media_id": media_id,
            "image_urls": image_urls,
            "status_data": status_data,
        }

    print("📋 [Instagram 2/4] カルーセル子コンテナを作成中...")
    child_container_ids = []
    child_status_data = []
    for index, image_url in enumerate(image_urls, start=1):
        child_id = create_image_container(image_url, carousel_item=True)
        print(f"   child {index}/{len(image_urls)}: {child_id}")
        child_status_data.append(wait_for_container(child_id))
        child_container_ids.append(child_id)

    print("⏳ [Instagram 3/4] 親カルーセルコンテナを作成/処理中...")
    carousel_container_id = create_carousel_container(child_container_ids, caption)
    status_data = wait_for_container(carousel_container_id)

    print("📢 [Instagram 4/4] カルーセル投稿を公開中...")
    media_id = publish_container(carousel_container_id)
    print(f"🎉 Instagramカルーセル投稿完了: {media_id}")

    return {
        "mode": "carousel",
        "container_id": carousel_container_id,
        "child_container_ids": child_container_ids,
        "media_id": media_id,
        "image_urls": image_urls,
        "status_data": status_data,
        "child_status_data": child_status_data,
    }


if __name__ == "__main__":
    post_instagram_carousel()
