import re
import feedparser
from dotenv import load_dotenv

load_dotenv()

# デフォルトのRSSフィード（自由に追加・変更可）
RSS_FEEDS = [
    ("NHKニュース",        "https://www3.nhk.or.jp/rss/news/cat0.xml"),
    ("はてなブックマーク", "https://b.hatena.ne.jp/hotentry.rss"),
    ("TechCrunch Japan",  "https://jp.techcrunch.com/feed/"),
    ("Gigazine",          "https://gigazine.net/news/rss_2.0/"),
]

def _strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text or '').strip()

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
                articles.append({
                    "source":  source_name,
                    "title":   entry.get("title", "").strip(),
                    "summary": summary,
                    "link":    entry.get("link", ""),
                })
        except Exception as e:
            print(f"⚠️  RSS取得エラー ({source_name}): {e}")

    print(f"   合計 {len(articles)} 件の記事を取得しました")
    return articles


if __name__ == "__main__":
    arts = fetch_articles()
    for a in arts[:5]:
        print(f"[{a['source']}] {a['title']}")
