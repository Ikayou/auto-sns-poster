"""
単枚ニュース画像生成パイプライン

実行手順:
  1. RSSから記事を取得
  2. GPT-4o-miniで1枚画像用コンテンツ(JSON)を生成
  3. 関連画像を記事から取得
  4. HTMLテンプレートに流し込み
  5. Playwrightで単枚PNG化
  6. output/carousel/slide_01.png に保存
"""

import os
import sys
import json
import base64
import asyncio
import html
import mimetypes
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加（python app/create_carousel.py でも動くように）
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from dotenv import load_dotenv
import requests

from app.fetch_content import fetch_articles

load_dotenv()

client = OpenAI()

ROOT_DIR      = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT_DIR / "templates"
ASSETS_DIR    = ROOT_DIR / "assets"
OUTPUT_DIR    = ROOT_DIR / "output" / "carousel"
FONT_PATH     = ASSETS_DIR / "NotoSansJP-Bold.ttf"

# CTA スライドに表示するアカウント名（.env に TIKTOK_ACCOUNT_NAME を設定するか直接書き換える）
ACCOUNT_NAME  = os.getenv("TIKTOK_ACCOUNT_NAME", "german.news69")
NEWS_COUNT    = int(os.getenv("NEWS_COUNT", "5"))


# ---------------------------------------------------------------------------
# 1. コンテンツ生成
# ---------------------------------------------------------------------------

def generate_single_news_content(articles: list[dict]) -> dict:
    """RSS記事一覧を渡してAIに単枚ニュース画像用コンテンツを生成させる"""
    articles_text = "\n".join(
        f"[{i}] {a['title']}\n{a['summary']}\n{a['link']}"
        for i, a in enumerate(articles[:10], start=1)
    )

    image_candidates = "\n".join(
        f"[{i}] image_url={a.get('image_url') or '(none)'}"
        for i, a in enumerate(articles[:10], start=1)
    )

    prompt = f"""Du bist Tech-News-Redakteur fuer deutschsprachige TikTok-Beitraege.
Waehle aus den folgenden heise.de-Artikeln genau einen Artikel aus, der sich am besten
fuer eine einzelne Infografik eignet. Erstelle kurze, klare und faktentreue deutsche Texte.

【Artikel】
{articles_text}

【Bildkandidaten】
{image_candidates}

【Regeln】
- Verwende nur Informationen aus den heise.de-Artikeln oben.
- Keine unbestaetigten Vorwuerfe, Skandale oder zugespitzten Behauptungen.
- Alle sichtbaren Texte fuer die Bilder muessen Deutsch sein.
- title: maximal 42 Zeichen.
- summary: maximal 110 Zeichen.
- points: genau 3 Punkte, jeweils maximal 70 Zeichen.
- selected_index ist die Nummer des ausgewaehlten Artikels.
- image_url ist die Bild-URL des gewaehlten Artikels, sonst ein leerer String.
- caption endet mit einer Frage, die Kommentare anregt.

【Ausgabeformat: nur JSON】
{{
  "selected_index": 1,
  "tag": "Tech-News",
  "title": "Kurze deutsche Headline",
  "summary": "Kurze deutsche Zusammenfassung",
  "points": ["Punkt 1", "Punkt 2", "Punkt 3"],
  "caption": "Deutsche Caption ohne Hashtags",
  "hashtags": ["#TechNews", "#KI", "#IT", "#heise", "#News"],
  "image_url": "Bild-URL oder leerer String"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = json.loads(response.choices[0].message.content)

    selected_index = int(content.get("selected_index") or 1)
    selected_index = max(1, min(selected_index, len(articles)))
    article = articles[selected_index - 1]
    content["source"] = article.get("source", "heise online")
    content["article_title"] = article.get("title", "")
    content["link"] = article.get("link", "")
    content["image_url"] = content.get("image_url") or article.get("image_url", "")
    return content


def generate_carousel_content(articles: list[dict]) -> dict:
    """heise.deの記事から複数ニュース画像用のコンテンツを生成する。"""
    count = max(1, min(NEWS_COUNT, len(articles)))
    articles_text = "\n".join(
        f"[{i}] {a['title']}\n{a['summary']}\n{a['link']}"
        for i, a in enumerate(articles[:12], start=1)
    )

    image_candidates = "\n".join(
        f"[{i}] image_url={a.get('image_url') or '(none)'}"
        for i, a in enumerate(articles[:12], start=1)
    )

    prompt = f"""Du bist Tech-News-Redakteur fuer deutschsprachige TikTok-Beitraege.
Waehle aus den folgenden heise.de-Artikeln {count} unterschiedliche News aus.
Erstelle fuer jede News die Texte fuer genau eine Infografik. Alle sichtbaren Bildtexte
muessen Deutsch sein.

【Artikel】
{articles_text}

【Bildkandidaten】
{image_candidates}

【Regeln】
- Verwende nur Informationen aus den heise.de-Artikeln oben.
- Waehle denselben Artikel nicht mehrfach.
- Keine unbestaetigten Vorwuerfe, Skandale oder zugespitzten Behauptungen.
- title: maximal 42 Zeichen.
- summary: maximal 110 Zeichen.
- points: genau 3 Punkte, jeweils maximal 70 Zeichen.
- selected_index ist die Nummer des ausgewaehlten Artikels.
- image_url ist die Bild-URL des gewaehlten Artikels, sonst ein leerer String.
- caption stellt die 5 News vor und endet mit einer Kommentarfrage.

【Ausgabeformat: nur JSON】
{{
  "caption": "Deutsche Caption fuer alle 5 News, ohne Hashtags",
  "hashtags": ["#TechNews", "#KI", "#IT", "#heise", "#News"],
  "items": [
    {{
      "selected_index": 1,
      "tag": "Tech-News",
      "title": "Kurze deutsche Headline",
      "summary": "Kurze deutsche Zusammenfassung",
      "points": ["Punkt 1", "Punkt 2", "Punkt 3"],
      "image_url": "Bild-URL oder leerer String"
    }}
  ]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = json.loads(response.choices[0].message.content)
    items = content.get("items") or []

    enriched_items = []
    used_indexes = set()
    for item in items:
        try:
            selected_index = int(item.get("selected_index") or 1)
        except (TypeError, ValueError):
            selected_index = 1
        selected_index = max(1, min(selected_index, len(articles)))
        if selected_index in used_indexes:
            continue
        used_indexes.add(selected_index)

        article = articles[selected_index - 1]
        item["source"] = article.get("source", "heise online")
        item["article_title"] = article.get("title", "")
        item["link"] = article.get("link", "")
        item["image_url"] = item.get("image_url") or article.get("image_url", "")
        enriched_items.append(item)
        if len(enriched_items) >= count:
            break

    for index, article in enumerate(articles, start=1):
        if len(enriched_items) >= count:
            break
        if index in used_indexes:
            continue
        enriched_items.append({
            "selected_index": index,
            "tag": "Tech-News",
            "title": article.get("title", "")[:20],
            "summary": article.get("summary", "")[:75],
            "points": [
                "Aus den aktuellen heise.de-Artikeln ausgewaehlt",
                "Details stehen im verlinkten Originalartikel",
                "Die wichtigste Entwicklung kurz zusammengefasst",
            ],
            "source": article.get("source", "heise online"),
            "article_title": article.get("title", ""),
            "link": article.get("link", ""),
            "image_url": article.get("image_url", ""),
        })

    content["items"] = enriched_items
    content.setdefault("caption", "Fuenf aktuelle Tech-News von heise.de. Welche Meldung findest du am spannendsten?")
    content.setdefault("hashtags", ["#TechNews", "#KI", "#IT", "#heise", "#News"])
    return content


def generate_legacy_carousel_content(articles: list[dict]) -> dict:
    """以前の複数枚カルーセル用ジェネレーター。現在の通常実行では未使用。"""
    articles_text = "\n".join(
        f"[{a['source']}] {a['title']}\n{a['summary']}"
        for a in articles[:12]
    )

    prompt = f"""Du bist Produzent fuer deutschsprachige TikTok-Karussells.
Waehle aus den folgenden heise.de-Tech-News ein interessantes Thema aus und erstelle
faktentreue deutsche Karussell-Texte.

【Artikel】
{articles_text}

【Regeln】
- Verwende nur Informationen aus den heise.de-Artikeln oben.
- Keine unbestaetigten Vorwuerfe, Skandale oder zugespitzten Behauptungen.
- Nicht uebertreiben, sondern als nuetzliche Tech-News einordnen.
- Content-Slides: 4 bis 5.
- title: kurze starke Headline, maximal 42 Zeichen.
- heading: maximal 32 Zeichen, body: maximal 120 Zeichen.
- caption endet mit einer Frage, die Kommentare anregt.

【Ausgabeformat: nur JSON】
{{
  "tag":      "Kategorie, z.B. Tech-News",
  "title":    "Kurze deutsche Hauptheadline",
  "subtitle": "Kurzer deutscher Untertitel",
  "slides": [
    {{"heading": "Kurze Headline", "body": "Kurzer deutscher Text"}},
    ...
  ],
  "cta_text": "Follow-Hinweis mit \\n fuer Zeilenumbruch",
  "caption":  "Deutsche Caption ohne Hashtags",
  "hashtags": ["#TechNews", "#KI", "#IT", "#heise", "#News"]
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
        replacement = str(value)
        if key != "IMAGE_DATA_URI":
            replacement = html_escape(replacement)
        html = html.replace(f"{{{{{key}}}}}", replacement)
    return html


def html_escape(value: str) -> str:
    return html.escape(value or "", quote=True)


def _download_image_as_data_uri(image_url: str) -> str:
    if not image_url:
        return ""

    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.get(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 auto-sns-poster"},
            timeout=20,
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            content_type = mimetypes.guess_type(image_url)[0] or "image/jpeg"
        encoded = base64.b64encode(resp.content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
    except Exception as exc:
        print(f"⚠️  関連画像の取得に失敗しました: {image_url} ({exc})")
        return ""


# ---------------------------------------------------------------------------
# 3. Playwright で PNG 化
# ---------------------------------------------------------------------------

async def _render_all(content: dict) -> list[Path]:
    from playwright.async_api import async_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old_slide in OUTPUT_DIR.glob("slide_*.png"):
        old_slide.unlink()

    font_b64 = _get_font_b64()
    paths = []
    items = content.get("items") or [content]
    news_total = len(items)
    date_text = datetime.now().strftime("%d.%m.%Y")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        async def screenshot(html: str, path: Path):
            page = await browser.new_page(viewport={"width": 1080, "height": 1350})
            await page.set_content(html, wait_until="networkidle")
            await page.screenshot(path=str(path), full_page=False)
            await page.close()

        cover_html = _render_html("heise_cover.html", {
            "DATE": date_text,
            "ACCOUNT_NAME": ACCOUNT_NAME.lstrip("@"),
        }, font_b64)
        p = OUTPUT_DIR / "slide_01.png"
        await screenshot(cover_html, p)
        paths.append(p)
        print("  ✅ slide_01.png [表紙]")

        for idx, item in enumerate(items, start=1):
            points = (item.get("points") or [])[:3]
            while len(points) < 3:
                points.append("")
            image_data_uri = _download_image_as_data_uri(item.get("image_url", ""))

            kicker = item.get("kicker") or item.get("article_title") or item.get("source", "heise online")
            if len(kicker) > 68:
                kicker = kicker[:65].rstrip() + "..."

            single_html = _render_html("single_news.html", {
                "DATE": date_text,
                "CURRENT_PAD": f"{idx:02d}",
                "TOTAL_PAD": f"{news_total:02d}",
                "TAG": item.get("tag", "Tech-News"),
                "KICKER": kicker,
                "TITLE": item.get("title", ""),
                "SUMMARY": item.get("summary", ""),
                "POINT_1": points[0],
                "POINT_2": points[1],
                "POINT_3": points[2],
                "SOURCE": item.get("source", "heise online"),
                "ACCOUNT_NAME": ACCOUNT_NAME.lstrip("@"),
                "IMAGE_DATA_URI": image_data_uri,
                "NO_IMAGE_DISPLAY": "none" if image_data_uri else "flex",
            }, font_b64)
            p = OUTPUT_DIR / f"slide_{idx + 1:02d}.png"
            await screenshot(single_html, p)
            paths.append(p)
            print(f"  ✅ slide_{idx + 1:02d}.png [{idx}/{news_total} ニュース画像]")

        outro_html = _render_html("heise_outro.html", {
            "DATE": date_text,
            "ACCOUNT_NAME": ACCOUNT_NAME.lstrip("@"),
        }, font_b64)
        p = OUTPUT_DIR / f"slide_{news_total + 2:02d}.png"
        await screenshot(outro_html, p)
        paths.append(p)
        print(f"  ✅ slide_{news_total + 2:02d}.png [終了ページ]")

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
