"""
TikTok フォトカルーセル投稿

フロー:
  ローカルPNG → GitHub Pages リポジトリに git push
  → 公開URL取得 → TikTok Content Posting API (PULL_FROM_URL) で投稿

TikTok の仕様:
  - 写真投稿は PULL_FROM_URL のみ対応（FILE_UPLOAD 非対応）
  - PULL_FROM_URL は「所有が確認済みのドメイン」のみ使用可能
  → GitHub Pages (username.github.io) で解決

事前準備（初回のみ）:
  1. GitHub にリポジトリ作成（例: your-github-username/tiktok-slides）
  2. Settings → Pages → Source: Deploy from branch(main) を有効化
  3. .env に設定:
       GITHUB_SLIDES_DIR   = /path/to/local/tiktok-slides（cloneしたローカルパス）
       GITHUB_PAGES_BASE_URL = https://your-github-username.github.io/tiktok-slides
  4. TikTok Developer Portal → あなたのアプリ → URL properties
     → "https://your-github-username.github.io/tiktok-slides/" を追加・認証
       認証方法: リポジトリのルートに tiktok-verification.txt を設置

実行:
  python app/post_tiktok_carousel.py
"""

import os
import json
import time
import shutil
import subprocess
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()

ACCESS_TOKEN     = os.getenv("TIKTOK_ACCESS_TOKEN", "")
SLIDES_REPO      = os.getenv("GITHUB_SLIDES_REPO", "")      # GitHub Pages リポジトリURL
SLIDES_DIR       = os.getenv("GITHUB_SLIDES_DIR", "") or ("/tmp/auto-sns-slides" if SLIDES_REPO else "")
SLIDES_BRANCH    = os.getenv("GITHUB_SLIDES_BRANCH") or "main"
PAGES_BASE_URL   = os.getenv("GITHUB_PAGES_BASE_URL", "")   # https://user.github.io/repo
BASE_URL         = "https://open.tiktokapis.com/v2"
POST_MODE        = "DIRECT_POST"
PRIVACY_LEVEL    = "SELF_ONLY"   # TikTok の「自分のみ」投稿

PAGES_DEPLOY_WAIT = 90   # GitHub Pages デプロイ待機秒数
PHOTO_TITLE_LIMIT = 90
PHOTO_DESCRIPTION_LIMIT = 4000


# ---------------------------------------------------------------------------
# Step 1: GitHub Pages に画像を push して公開 URL を返す
# ---------------------------------------------------------------------------

def push_to_github_pages(image_paths: list[Path]) -> list[str]:
    """PNG を GitHub Pages リポジトリに push して公開 URL リストを返す"""
    if not SLIDES_DIR:
        raise ValueError(
            "GITHUB_SLIDES_DIR が .env に設定されていません\n"
            "GitHub Pages リポジトリをクローンしたローカルパスを設定してください"
        )
    if not PAGES_BASE_URL:
        raise ValueError(
            "GITHUB_PAGES_BASE_URL が .env に設定されていません\n"
            "例: https://your-github-username.github.io/tiktok-slides"
        )

    dest_dir = Path(SLIDES_DIR)

    def clone_url_with_token() -> str:
        github_token = os.getenv("GITHUB_TOKEN", "")
        if github_token and SLIDES_REPO.startswith("https://github.com/"):
            return SLIDES_REPO.replace(
                "https://github.com/",
                f"https://x-access-token:{github_token}@github.com/",
                1,
            )
        return SLIDES_REPO

    def repo_name(repo_url: str) -> str:
        parsed = urlparse(repo_url)
        path = parsed.path.rstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        return path.split("/")[-1]

    def clone_repo():
        clone_cmd = ["git", "clone", "--branch", SLIDES_BRANCH, clone_url_with_token(), str(dest_dir)]
        result = subprocess.run(clone_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return

        if "Remote branch" in result.stderr and "not found" in result.stderr:
            fallback_cmd = ["git", "clone", clone_url_with_token(), str(dest_dir)]
            fallback = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if fallback.returncode == 0:
                return
            raise RuntimeError(f"git command failed: {' '.join(fallback_cmd)}\n{fallback.stderr}")

        raise RuntimeError(f"git command failed: {' '.join(clone_cmd)}\n{result.stderr}")

    if not dest_dir.exists() and SLIDES_REPO:
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        clone_repo()
    elif not (dest_dir / ".git").exists() and SLIDES_REPO:
        if any(dest_dir.iterdir()):
            raise RuntimeError(f"GITHUB_SLIDES_DIR is not empty and is not a git repo: {dest_dir}")
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        clone_repo()
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)

    # git pull → copy images → add → commit → push
    def run_git(args: list[str], allow_fail_msgs: list[str] = []) -> subprocess.CompletedProcess:
        cmd = ["git", "-C", str(dest_dir)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            combined = result.stdout + result.stderr
            if any(msg in combined for msg in allow_fail_msgs):
                return result
            raise RuntimeError(f"git コマンド失敗: {' '.join(cmd)}\n{result.stderr}")
        return result

    if SLIDES_REPO:
        current_remote = run_git(["remote", "get-url", "origin"]).stdout.strip()
        if repo_name(current_remote) != repo_name(SLIDES_REPO):
            raise RuntimeError(
                "GITHUB_SLIDES_DIR points to a different git repository. "
                f"dir={dest_dir}, origin={current_remote}, expected={SLIDES_REPO}"
            )

    run_git(["config", "user.name", os.getenv("GIT_COMMITTER_NAME", "github-actions[bot]")])
    run_git(["config", "user.email", os.getenv("GIT_COMMITTER_EMAIL", "github-actions[bot]@users.noreply.github.com")])
    run_git(["checkout", "-B", SLIDES_BRANCH])

    run_git(["pull", "--rebase", "origin", SLIDES_BRANCH],
            allow_fail_msgs=[
                "There is no tracking information",
                "no tracking information",
                "couldn't find remote ref",
                "Couldn't find remote ref",
            ])

    filenames = []
    for img_path in image_paths:
        dest = dest_dir / img_path.name
        shutil.copy2(img_path, dest)
        filenames.append(img_path.name)
        print(f"  📋 {img_path.name} → {dest}")

    run_git(["add", "."])
    run_git(["commit", "-m", "update slides"],
            allow_fail_msgs=["nothing to commit"])
    run_git(["push", "origin", SLIDES_BRANCH])

    print(f"  ✅ GitHub に push しました")
    print(f"  ⏳ GitHub Pages のデプロイ待機中（{PAGES_DEPLOY_WAIT}秒）...")
    time.sleep(PAGES_DEPLOY_WAIT)

    base = PAGES_BASE_URL.rstrip("/")
    urls = [f"{base}/{name}" for name in filenames]
    print(f"  ✅ 公開URL 生成完了")
    for url in urls:
        print(f"     {url}")
    return urls


# ---------------------------------------------------------------------------
# Step 2: TikTok API で投稿（PULL_FROM_URL）
# ---------------------------------------------------------------------------

def create_photo_post(photo_urls: list[str], caption: str, hashtags: list[str]) -> str:
    """TikTok にフォトカルーセルを投稿して publish_id を返す"""
    full_caption = caption + "\n\n" + " ".join(hashtags)
    title = caption[:PHOTO_TITLE_LIMIT] or "auto-sns-poster"
    description = full_caption[:PHOTO_DESCRIPTION_LIMIT]

    payload = {
        "post_info": {
            "title":           title,
            "description":     description,
            "privacy_level":   PRIVACY_LEVEL,
            "disable_comment": False,
        },
        "source_info": {
            "source":            "PULL_FROM_URL",
            "photo_images":      photo_urls,
            "photo_cover_index": 0,
        },
        "media_type": "PHOTO",
        "post_mode":  POST_MODE,
    }

    print(f"   投稿モード: {POST_MODE} / 公開範囲: {PRIVACY_LEVEL}")
    print(f"   送信ペイロード: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    resp = requests.post(
        f"{BASE_URL}/post/publish/content/init/",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type":  "application/json; charset=UTF-8",
        },
        json=payload,
        timeout=30,
    )
    data = resp.json()
    print(f"   APIレスポンス [{resp.status_code}]: {data}")

    if resp.status_code != 200 or data.get("error", {}).get("code") != "ok":
        raise Exception(f"TikTok 投稿エラー: {data}")

    return data["data"]["publish_id"]


# ---------------------------------------------------------------------------
# Step 3: 投稿ステータスを確認
# ---------------------------------------------------------------------------

def check_publish_status(publish_id: str, timeout_sec: int = 120) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.post(
            f"{BASE_URL}/post/publish/status/fetch/",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={"publish_id": publish_id},
            timeout=15,
        )
        data = resp.json()
        status = data.get("data", {}).get("status", "PROCESSING")
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            return status
        print(f"   ステータス: {status} ... 10秒後に再確認")
        time.sleep(10)
    return "TIMEOUT"


# ---------------------------------------------------------------------------
# メイン関数
# ---------------------------------------------------------------------------

def post_carousel(image_paths: list[Path], caption: str, hashtags: list[str]) -> str:
    print(f"🚀 TikTokカルーセル投稿を開始します（{len(image_paths)} 枚）")

    # 1. GitHub Pages に push
    print("\n📤 [1/3] GitHub Pages に画像を push 中...")
    photo_urls = push_to_github_pages(image_paths)

    # 2. TikTok に投稿
    print("\n📋 [2/3] TikTok に投稿中...")
    publish_id = create_photo_post(photo_urls, caption, hashtags)
    print(f"   publish_id: {publish_id}")

    # 3. ステータス確認
    print("\n⏳ [3/3] 投稿ステータスを確認中...")
    status = check_publish_status(publish_id)
    print(f"   最終ステータス: {status}")

    if status == "PUBLISH_COMPLETE":
        print(f"\n🎉 TikTokへの非公開投稿が完了しました！ publish_id: {publish_id}")
    else:
        print(f"\n⚠️  ステータス: {status}（TikTokアプリで確認してください）")

    return publish_id


# ---------------------------------------------------------------------------
# 単体実行
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    carousel_dir = Path("output/carousel")
    image_paths  = sorted(carousel_dir.glob("slide_*.png"))

    if not image_paths:
        print("❌ output/carousel/ にスライド画像が見つかりません")
        raise SystemExit(1)

    content_path = Path("assets/carousel_content.json")
    if not content_path.exists():
        print("❌ assets/carousel_content.json が見つかりません")
        raise SystemExit(1)

    with open(content_path, encoding="utf-8") as f:
        content = json.load(f)

    post_carousel(image_paths, content["caption"], content["hashtags"])
