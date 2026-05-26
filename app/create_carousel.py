"""
カルーセル動画生成パイプライン

実行手順:
  1. RSSから記事を取得
  2. GPT-4o-miniでカルーセルコンテンツ(JSON)を生成
  3. HTMLテンプレートに流し込み
  4. Playwrightで各スライドをPNG化
  5. output/carousel/ に保存
"""

import os
import sys
import json
import base64
import asyncio
from pathlib import Path

# プロジェクトルートをパスに追加（python app/create_carousel.py でも動くように）
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from dotenv import load_dotenv

from app.fetch_content import fetch_articles

load_dotenv()

client = OpenAI()

ROOT_DIR      = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT_DIR / "templates"
ASSETS_DIR    = ROOT_DIR / "assets"
OUTPUT_DIR    = ROOT_DIR / "output" / "carousel"
FONT_PATH     = ASSETS_DIR / "NotoSansJP-Bold.ttf"

# CTA スライドに表示するアカウント名（.env に TIKTOK_ACCOUNT_NAME を設定するか直接書き換える）
ACCOUNT_NAME  = os.getenv("TIKTOK_ACCOUNT_NAME", "your_account")


# ---------------------------------------------------------------------------
# 1. コンテンツ生成
# ---------------------------------------------------------------------------

def generate_carousel_content(articles: list[dict]) -> dict:
    """RSS記事一覧を渡してAIにカルーセルコンテンツを生成させる"""
    articles_text = "\n".join(
        f"[{a['source']}] {a['title']}\n{a['summary']}"
        for a in articles[:12]
    )

    prompt = f"""あなたはZ世代に刺さるTikTokカルーセル投稿のプロデューサーです。
以下のニュース記事から最もバズりそうなトピックを1つ選び、
「知らないと損する」「え、まじ！？」と思わせるカルーセルコンテンツを生成してください。

【記事一覧】
{articles_text}

【ルール】
- コンテンツスライドは 4〜5 枚
- 1枚目タイトルは「続きが気になる」強いフック（20文字以内）
- 各スライドの heading は 15文字以内、body は 80文字以内
- キャプションは視聴者にコメントを促す質問で締める

【出力形式（JSONのみ）】
{{
  "tag":      "カテゴリタグ（例: テック速報）",
  "title":    "メインタイトル（20文字以内）",
  "subtitle": "サブタイトル補足（30文字以内）",
  "slides": [
    {{"heading": "見出し（15文字以内）", "body": "本文（80文字以内）"}},
    ...
  ],
  "cta_text": "フォロー誘導テキスト（2行、改行は\\nで）",
  "caption":  "キャプション文（ハッシュタグなし）",
  "hashtags": ["#タグ1", "#タグ2", "#タグ3", "#タグ4", "#タグ5"]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# 2. HTMLレンダリング
# ---------------------------------------------------------------------------

def _get_font_b64() -> str:
    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"フォントが見つかりません: {FONT_PATH}\n"
            "assets/NotoSansJP-Bold.ttf を配置してください。"
        )
    with open(FONT_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _render_html(template_name: str, variables: dict, font_b64: str) -> str:
    template_path = TEMPLATES_DIR / template_name
    with open(template_path, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{FONT_B64}}", font_b64)
    for key, value in variables.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return html


# ---------------------------------------------------------------------------
# 3. Playwright で PNG 化
# ---------------------------------------------------------------------------

async def _render_all(content: dict) -> list[Path]:
    from playwright.async_api import async_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    font_b64    = _get_font_b64()
    slides_data = content["slides"]
    total       = len(slides_data) + 2  # タイトル + コンテンツ + CTA
    paths       = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def screenshot(html: str, path: Path):
            page = await browser.new_page(viewport={"width": 1080, "height": 1920})
            await page.set_content(html, wait_until="networkidle")
            await page.screenshot(path=str(path), full_page=False)
            await page.close()

        # --- スライド 1: タイトル ---
        title_html = _render_html("slide_title.html", {
            "TAG":      content["tag"],
            "TITLE":    content["title"],
            "SUBTITLE": content["subtitle"],
            "TOTAL":    total,
        }, font_b64)
        p = OUTPUT_DIR / "slide_01.png"
        await screenshot(title_html, p)
        paths.append(p)
        print(f"  ✅ slide 1/{total}  [タイトル]")

        # --- スライド 2〜N: コンテンツ ---
        for i, slide in enumerate(slides_data, start=1):
            html = _render_html("slide_content.html", {
                "INDEX":   i,
                "HEADING": slide["heading"],
                "BODY":    slide["body"],
                "CURRENT": i + 1,
                "TOTAL":   total,
            }, font_b64)
            p = OUTPUT_DIR / f"slide_{i+1:02d}.png"
            await screenshot(html, p)
            paths.append(p)
            print(f"  ✅ slide {i+1}/{total}  [ポイント {i}]")

        # --- 最後: CTA ---
        cta_html = _render_html("slide_cta.html", {
            "CTA_TEXT":     content.get("cta_text", "フォローして\n最新情報をゲット！"),
            "ACCOUNT_NAME": ACCOUNT_NAME,
            "CURRENT":      total,
            "TOTAL":        total,
        }, font_b64)
        p = OUTPUT_DIR / f"slide_{total:02d}.png"
        await screenshot(cta_html, p)
        paths.append(p)
        print(f"  ✅ slide {total}/{total}  [CTA]")

        await browser.close()

    return paths


def render_slides(content: dict) -> list[Path]:
    return asyncio.run(_render_all(content))


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("📰 RSSフィードから記事を取得中...")
    articles = fetch_articles()

    print("🤖 AIがカルーセルコンテンツを生成中...")
    content = generate_carousel_content(articles)
    print("\n--- 生成されたコンテンツ ---")
    print(json.dumps(content, ensure_ascii=False, indent=2))

    ASSETS_DIR.mkdir(exist_ok=True)
    with open(ASSETS_DIR / "carousel_content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    print("\n🎨 Playwrightでスライド画像を生成中...")
    png_paths = render_slides(content)

    print(f"\n✨ 完了！ {len(png_paths)} 枚を {OUTPUT_DIR} に保存しました")
    for p in png_paths:
        print(f"   {p.name}")
