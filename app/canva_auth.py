"""
Canva Connect API — OAuth 2.0 クライアント認証

事前準備:
  1. https://www.canva.com/developers/ でアプリを作成
  2. Client Credentials を .env に設定:
       CANVA_CLIENT_ID=AAA...
       CANVA_CLIENT_SECRET=xxx...
  3. アプリに "design:content:write", "design:content:read",
     "asset:read", "asset:write", "brandtemplate:content:read" の
     スコープを付与する
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"

_token_cache: dict = {}


def get_access_token() -> str:
    """Client Credentials フローでアクセストークンを取得（キャッシュ付き）"""
    now = time.time()
    if _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["access_token"]

    client_id = os.getenv("CANVA_CLIENT_ID")
    client_secret = os.getenv("CANVA_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "CANVA_CLIENT_ID と CANVA_CLIENT_SECRET を .env に設定してください\n"
            "取得先: https://www.canva.com/developers/"
        )

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": (
                "design:content:write design:content:read "
                "asset:read asset:write brandtemplate:content:read"
            ),
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["access_token"]


def canva_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }
