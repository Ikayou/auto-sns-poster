import os
from urllib.parse import unquote

import requests
from dotenv import load_dotenv


load_dotenv()

CLIENT_KEY = os.getenv("CLIENT_KEY") or os.getenv("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.getenv("CLIENT_SECRET") or os.getenv("TIKTOK_CLIENT_SECRET")
CODE = os.getenv("CODE")
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://ikayou.github.io/tiktok-api-legal/")


def require_env(name: str, value: str | None) -> str:
    if not value:
        raise SystemExit(f"{name} is missing in .env")
    return value


def exchange_user_token() -> None:
    client_key = require_env("CLIENT_KEY", CLIENT_KEY)
    client_secret = require_env("CLIENT_SECRET", CLIENT_SECRET)
    code = require_env("CODE", CODE)

    response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "code": unquote(code),
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        raise SystemExit(f"TikTok token response was not JSON: {response.text}")

    if response.status_code != 200 or "access_token" not in data or "refresh_token" not in data:
        raise SystemExit(f"TikTok token error {response.status_code}: {data}")

    print("Access token:")
    print(data["access_token"])
    print()
    print("Refresh token:")
    print(data["refresh_token"])
    print()
    print("Paste the refresh token into .env as TIKTOK_REFRESH_TOKEN=...")
    print("Paste the same refresh token into the GitHub Secret TIKTOK_REFRESH_TOKEN.")
    print("TIKTOK_ACCESS_TOKEN is optional and only useful for temporary one-off runs.")
    print("Then run: python app/check_tiktok_info.py")


if __name__ == "__main__":
    exchange_user_token()
