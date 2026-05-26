"""
TikTokアカウントの投稿可能な機能を確認する診断スクリプト
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
BASE_URL     = "https://open.tiktokapis.com/v2"

def check_creator_info():
    url     = f"{BASE_URL}/post/publish/creator_info/query/"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type":  "application/json; charset=UTF-8",
    }
    resp = requests.post(url, json={}, headers=headers)
    print(f"ステータス: {resp.status_code}")
    import json
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    check_creator_info()
