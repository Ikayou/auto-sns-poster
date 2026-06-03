"""
Agent-driven daily posting flow.

実行:
  python app/agent_runner.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.create_carousel import ASSETS_DIR, OUTPUT_DIR, generate_carousel_content, render_slides  # noqa: E402
from app.fetch_content import RSS_FEEDS, fetch_articles  # noqa: E402
from app.post_to_instagram_carousel import post_instagram_carousel  # noqa: E402
from app.slides_to_video import slides_to_video  # noqa: E402
from app.upload_to_tiktok_draft import upload_to_tiktok_draft  # noqa: E402


load_dotenv()

client = OpenAI()

AGENT_PLAN_PATH = ASSETS_DIR / "agent_plan.json"
CONTENT_REVIEW_PATH = ASSETS_DIR / "content_review.json"
CONTENT_PATH = ASSETS_DIR / "carousel_content.json"
try:
    DEFAULT_CAROUSEL_COUNT = int(os.getenv("NEWS_COUNT", "5"))
except ValueError:
    DEFAULT_CAROUSEL_COUNT = 5
UPLOAD_TO_TIKTOK = os.getenv("UPLOAD_TO_TIKTOK", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
UPLOAD_TO_INSTAGRAM = os.getenv("UPLOAD_TO_INSTAGRAM", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _article_digest(articles: list[dict], limit: int = 18) -> str:
    return "\n".join(
        (
            f"[{index}] source={article.get('source', '')}\n"
            f"title={article.get('title', '')}\n"
            f"summary={article.get('summary', '')}\n"
            f"link={article.get('link', '')}"
        )
        for index, article in enumerate(articles[:limit], start=1)
    )


def decide_post_plan(articles: list[dict]) -> dict:
    """Agentが digest / carousel のどちらで投稿するかを決める。skipは許可しない。"""
    if not articles:
        raise RuntimeError("RSS記事が0件だったため投稿を作成できません。")

    prompt = f"""Du bist ein verantwortlicher Social-Media-Redaktionsagent.
Entscheide fuer den heutigen TikTok-Beitrag, ob wir fuenf News auf EINER
kompakten Infografik posten oder wie gewohnt fuenf News als Carousel-Video
mit je einer News pro Karte.

Wichtig:
- Du darfst NICHT skippen. Es muss immer gepostet werden.
- Erlaubte mode-Werte sind nur "digest" oder "carousel".
- Waehle "digest", wenn die Themen kurz genug sind, um als schnelle Top-5-
  Uebersicht auf einer Karte zu funktionieren.
- Waehle "carousel", wenn die fuenf Meldungen mehr Raum brauchen.
- Die Ausgabe muss reines JSON sein.

Verfuegbare Quellen:
{", ".join(name for name, _url in RSS_FEEDS)}

Artikel:
{_article_digest(articles)}

JSON-Format:
{{
  "mode": "digest",
  "news_count": 5,
  "reason": "Kurze Begruendung auf Deutsch",
  "editorial_angle": "Kurz die Perspektive des Beitrags",
  "priority_indexes": [1, 2, 3]
}}"""

    response = client.chat.completions.create(
        model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    plan = json.loads(response.choices[0].message.content)

    mode = plan.get("mode")
    if mode == "single_news":
        mode = "digest"
    if mode not in ("digest", "carousel"):
        mode = "carousel"

    try:
        news_count = int(plan.get("news_count") or DEFAULT_CAROUSEL_COUNT)
    except (TypeError, ValueError):
        news_count = DEFAULT_CAROUSEL_COUNT
    news_count = max(2, min(news_count, DEFAULT_CAROUSEL_COUNT, len(articles)))

    plan["mode"] = mode
    plan["news_count"] = news_count
    plan["decided_at"] = datetime.now().isoformat(timespec="seconds")
    plan["rss_sources"] = [{"name": name, "url": url} for name, url in RSS_FEEDS]
    return plan


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _limit_text(value: str | None, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _sanitize_reviewed_content(original: dict, reviewed: dict, plan: dict) -> dict:
    reviewed_content = reviewed.get("content") if isinstance(reviewed, dict) else None
    if not isinstance(reviewed_content, dict):
        reviewed_content = {}

    cleaned = dict(original)
    for key, max_chars in (
        ("deck_tag", 28),
        ("deck_title", 24),
        ("caption", 500),
    ):
        if key in reviewed_content:
            cleaned[key] = _limit_text(reviewed_content.get(key), max_chars)

    hashtags = reviewed_content.get("hashtags")
    if isinstance(hashtags, list) and hashtags:
        cleaned["hashtags"] = [_limit_text(tag, 40) for tag in hashtags[:8]]

    reviewed_items = reviewed_content.get("items")
    original_items = original.get("items") or []
    if isinstance(reviewed_items, list):
        merged_items = []
        for index, original_item in enumerate(original_items):
            item = dict(original_item)
            reviewed_item = reviewed_items[index] if index < len(reviewed_items) else {}
            if isinstance(reviewed_item, dict):
                for key, max_chars in (
                    ("tag", 24),
                    ("title", 42),
                    ("summary", 110 if plan.get("mode") == "carousel" else 88),
                ):
                    if key in reviewed_item:
                        item[key] = _limit_text(reviewed_item.get(key), max_chars)

                points = reviewed_item.get("points")
                if isinstance(points, list):
                    safe_points = [_limit_text(point, 70) for point in points[:3]]
                    while len(safe_points) < 3:
                        safe_points.append("")
                    item["points"] = safe_points
            merged_items.append(item)
        cleaned["items"] = merged_items

    return cleaned


def review_content(content: dict, articles: list[dict], plan: dict) -> tuple[dict, dict]:
    """内容チェックAgent。投稿は止めず、問題があれば表示テキストを修正する。"""
    prompt = f"""Du bist ein strenger Faktencheck- und Stilreview-Agent fuer deutsche TikTok-News.
Pruefe den generierten Inhalt gegen die RSS-Artikel und korrigiere sichtbare Texte.

Wichtig:
- Nicht skippen. Der Beitrag muss weiter produziert werden.
- Keine neuen Fakten erfinden. Nutze nur die Artikelinformationen unten.
- Entferne Spekulation, Clickbait, unbestaetigte Vorwuerfe und uebertriebene Sprache.
- Deutsch muss natuerlich, kurz und sachlich sein.
- Vermeide doppelte News.
- Fuer mode=digest muss jede summary besonders kurz sein, weil 5 News auf eine Slide kommen.
- Gib reines JSON zurueck.

Plan:
{json.dumps(plan, ensure_ascii=False, indent=2)}

Artikel:
{_article_digest(articles)}

Aktueller Inhalt:
{json.dumps(content, ensure_ascii=False, indent=2)}

JSON-Format:
{{
  "review_summary": "Kurze Zusammenfassung der Pruefung auf Deutsch",
  "changes": ["Aenderung 1", "Aenderung 2"],
  "content": {{
    "deck_tag": "Top 5 Nachrichten",
    "deck_title": "Heute wichtig.",
    "caption": "Korrigierte Caption ohne Hashtags",
    "hashtags": ["#News", "#Deutschland"],
    "items": [
      {{
        "tag": "News",
        "title": "Korrigierter kurzer Titel",
        "summary": "Korrigierte kurze Zusammenfassung",
        "points": ["Punkt 1", "Punkt 2", "Punkt 3"]
      }}
    ]
  }}
}}"""

    response = client.chat.completions.create(
        model=os.getenv("REVIEW_AGENT_MODEL", os.getenv("AGENT_MODEL", "gpt-4o-mini")),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    review = json.loads(response.choices[0].message.content)
    cleaned_content = _sanitize_reviewed_content(content, review, plan)
    return cleaned_content, review


def _prioritize_articles(articles: list[dict], plan: dict) -> list[dict]:
    priority_indexes = plan.get("priority_indexes") or []
    selected = []
    seen = set()
    for raw_index in priority_indexes:
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if index < 1 or index > len(articles) or index in seen:
            continue
        selected.append(articles[index - 1])
        seen.add(index)

    selected.extend(
        article
        for index, article in enumerate(articles, start=1)
        if index not in seen
    )
    return selected


def run_agent_flow() -> dict:
    print("📰 複数RSSフィードから記事を取得中...")
    articles = fetch_articles()

    print("🤖 Agentが今日の投稿形式を判断中...")
    plan = decide_post_plan(articles)
    _save_json(AGENT_PLAN_PATH, plan)
    print(f"   mode={plan['mode']} / news_count={plan['news_count']}")
    print(f"   reason={plan.get('reason', '')}")
    articles_for_generation = _prioritize_articles(articles, plan)

    print("🧠 まとめニュース用コンテンツを生成中...")
    content = generate_carousel_content(
        articles_for_generation,
        news_count=plan["news_count"],
    )
    content.setdefault("deck_tag", "Top 5 Nachrichten")
    content.setdefault("deck_title", "Heute wichtig.")
    include_cover_outro = plan["mode"] == "carousel" or UPLOAD_TO_INSTAGRAM
    if UPLOAD_TO_INSTAGRAM:
        layout = "carousel"
    else:
        layout = "digest" if plan["mode"] == "digest" else "carousel"

    content["agent_plan"] = {
        "mode": plan["mode"],
        "news_count": plan["news_count"],
        "reason": plan.get("reason", ""),
        "editorial_angle": plan.get("editorial_angle", ""),
    }

    print("🔎 内容チェックAgentが事実性・表現・長さを確認中...")
    content, review = review_content(content, articles_for_generation, plan)
    content["content_review"] = {
        "review_summary": review.get("review_summary", ""),
        "changes": review.get("changes", []),
        "reviewed_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save_json(CONTENT_REVIEW_PATH, review)
    print(f"   review={review.get('review_summary', '')}")

    _save_json(CONTENT_PATH, content)

    print("🎨 スライド画像を生成中...")
    png_paths = render_slides(
        content,
        include_cover_outro=include_cover_outro,
        layout=layout,
    )
    print(f"   {len(png_paths)}枚を {OUTPUT_DIR} に保存しました")

    print("🎬 スライドを動画に変換中...")
    video_path = slides_to_video()

    if UPLOAD_TO_TIKTOK:
        print("🚀 TikTok下書き/編集フローへ送信中...")
        upload_result = upload_to_tiktok_draft(video_path, return_status=True)
        plan["publish_id"] = upload_result["publish_id"]
        plan["tiktok_upload_status"] = upload_result["status"]
        plan["tiktok_upload_status_data"] = upload_result["status_data"]
        _save_json(AGENT_PLAN_PATH, plan)
    else:
        print("UPLOAD_TO_TIKTOK=false のため、TikTok送信はスキップしました。")

    if UPLOAD_TO_INSTAGRAM:
        print("🚀 Instagramカルーセルへ公開中...")
        instagram_result = post_instagram_carousel(png_paths, content)
        plan["instagram_post_mode"] = instagram_result["mode"]
        plan["instagram_container_id"] = instagram_result["container_id"]
        plan["instagram_child_container_ids"] = instagram_result["child_container_ids"]
        plan["instagram_media_id"] = instagram_result["media_id"]
        plan["instagram_image_urls"] = instagram_result["image_urls"]
        plan["instagram_upload_status_data"] = instagram_result["status_data"]
        _save_json(AGENT_PLAN_PATH, plan)
    else:
        print("UPLOAD_TO_INSTAGRAM=false のため、Instagram投稿はスキップしました。")

    return {
        "plan": plan,
        "content_path": str(CONTENT_PATH),
        "video_path": str(video_path),
    }


if __name__ == "__main__":
    run_agent_flow()
