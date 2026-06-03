import re
import os
from urllib.parse import urljoin

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

# デフォルトのRSSフィード。RSS_FEEDS 環境変数で上書きできる。
# 形式: "Name|https://example.com/feed.xml;Other|https://example.com/rss"
DEFAULT_RSS_FEEDS = [
    ("heise online", "https://www.heise.de/newsticker/heise-atom.xml"),
    ("Tagesschau", "https://www.tagesschau.de/index~rss2.xml"),
    
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def _parse_rss_feeds(value: str | None) -> list[tuple[str, str]]:
    if not value:
        return DEFAULT_RSS_FEEDS

    feeds = []
    for index, raw_item in enumerate(value.split(";"), start=1):
        item = raw_item.strip()
        if not item:
            continue
        if "|" in item:
            name, url = item.split("|", 1)
            source_name = name.strip() or f"RSS {index}"
            feed_url = url.strip()
        else:
            feed_url = item
            source_name = re.sub(r"^https?://(www\.)?", "", feed_url).split("/", 1)[0]
        if feed_url:
            feeds.append((source_name, feed_url))

    return feeds or DEFAULT_RSS_FEEDS


RSS_FEEDS = _parse_rss_feeds(os.getenv("RSS_FEEDS"))


def _strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text or '').strip()


def _first_image_from_html(html: str, base_url: str = "") -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "", flags=re.IGNORECASE)
        if match:
            return urljoin(base_url, match.group(1))
    return ""


def _extract_image_from_entry(entry: dict) -> str:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key, []) or []:
            url = media.get("url")
            if url:
                return url

    for enclosure in entry.get("enclosures", []) or []:
        url = enclosure.get("href") or enclosure.get("url")
        if url and str(enclosure.get("type", "")).startswith("image/"):
            return url

    for link in entry.get("links", []) or []:
        url = link.get("href")
        if url and str(link.get("type", "")).startswith("image/"):
            return url

    return _first_image_from_html(
        entry.get("summary") or entry.get("description") or "",
        entry.get("link", ""),
    )


def _fetch_article_image(url: str) -> str:
    if not url:
        return ""
    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.get(url, headers=REQUEST_HEADERS, timeout=15)
        resp.raise_for_status()
        return _first_image_from_html(resp.text, url)
    except Exception:
        return ""

def fetch_articles(max_per_feed: int = 5) -> list[dict]:
    """複数RSSフィードから記事を収集して返す"""
    articles = []
    for source_name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                summary = _strip_html(
                    entry.get("summary") or entry.get("description") or ""
                )[:400]
                link = entry.get("link", "")
                image_url = _extract_image_from_entry(entry) or _fetch_article_image(link)
                articles.append({
                    "source":  source_name,
                    "title":   entry.get("title", "").strip(),
                    "summary": summary,
                    "link":    link,
                    "image_url": image_url,
                })
        except Exception as e:
            print(f"⚠️  RSS取得エラー ({source_name}): {e}")

    print(f"   合計 {len(articles)} 件の記事を取得しました")
    return articles


if __name__ == "__main__":
    arts = fetch_articles()
    for a in arts[:5]:
        print(f"[{a['source']}] {a['title']}")
