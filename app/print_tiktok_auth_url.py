import os
from urllib.parse import urlencode

from dotenv import load_dotenv


load_dotenv()

CLIENT_KEY = os.getenv("CLIENT_KEY") or os.getenv("TIKTOK_CLIENT_KEY")
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://ikayou.github.io/tiktok-api-legal/")
SCOPES = os.getenv("TIKTOK_SCOPES", "user.info.basic,video.upload,video.publish")


def main() -> None:
    if not CLIENT_KEY:
        raise SystemExit("CLIENT_KEY is missing in .env")

    params = {
        "client_key": CLIENT_KEY,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
    }
    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params)

    print("Open this URL while logged in to the TikTok account that should receive drafts:")
    print(auth_url)
    print()
    print("After approval, copy the code= value from the redirected URL into .env as CODE=...")


if __name__ == "__main__":
    main()
