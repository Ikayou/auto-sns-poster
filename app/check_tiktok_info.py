"""
TikTokアカウントの投稿可能な機能を確認する診断スクリプト
"""
import requests
from tiktok_token import get_access_token

BASE_URL     = "https://open.tiktokapis.com/v2"

def check_creator_info():
    access_token = get_access_token()
    url     = f"{BASE_URL}/post/publish/creator_info/query/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json; charset=UTF-8",
    }
    resp = requests.post(url, json={}, headers=headers)
    print(f"ステータス: {resp.status_code}")
    import json
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    check_creator_info()
