"""
TikTok OAuth token helpers.

Prefer TIKTOK_REFRESH_TOKEN for automation. TIKTOK_ACCESS_TOKEN is kept as a
temporary fallback for one-off local runs.
"""

from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://open.tiktokapis.com/v2"


def clean_token(value: str | None) -> str:
    if not value:
        return ""

    token = value.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        token = token[1:-1].strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def _env(*names: str) -> str:
    for name in names:
        value = clean_token(os.getenv(name))
        if value:
            return value
    return ""


def refresh_access_token(
    refresh_token: str | None = None,
    client_key: str | None = None,
    client_secret: str | None = None,
) -> str:
    refresh_token = clean_token(refresh_token) or _env("TIKTOK_REFRESH_TOKEN")
    client_key = clean_token(client_key) or _env("TIKTOK_CLIENT_KEY", "CLIENT_KEY")
    client_secret = clean_token(client_secret) or _env("TIKTOK_CLIENT_SECRET", "CLIENT_SECRET")

    missing = [
        name
        for name, value in (
            ("TIKTOK_REFRESH_TOKEN", refresh_token),
            ("TIKTOK_CLIENT_KEY", client_key),
            ("TIKTOK_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing TikTok OAuth setting(s): {', '.join(missing)}")

    response = requests.post(
        f"{BASE_URL}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"TikTok token refresh response was not JSON: {response.text}") from exc

    access_token = clean_token(data.get("access_token"))
    if response.status_code != 200 or not access_token:
        raise RuntimeError(f"TikTok token refresh failed [{response.status_code}]: {data}")

    new_refresh_token = clean_token(data.get("refresh_token"))
    if new_refresh_token and new_refresh_token != refresh_token:
        print(
            "TikTok returned a new refresh token. Update the GitHub Secret "
            "TIKTOK_REFRESH_TOKEN with the latest refresh token soon."
        )

    return access_token


def get_access_token() -> str:
    if _env("TIKTOK_REFRESH_TOKEN"):
        print("Refreshing TikTok access token from TIKTOK_REFRESH_TOKEN...")
        return refresh_access_token()

    access_token = _env("TIKTOK_ACCESS_TOKEN")
    if access_token:
        print("Using TIKTOK_ACCESS_TOKEN directly. Prefer TIKTOK_REFRESH_TOKEN for automation.")
        return access_token

    raise RuntimeError(
        "Set TIKTOK_REFRESH_TOKEN with TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET, "
        "or set TIKTOK_ACCESS_TOKEN for a temporary one-off run."
    )
