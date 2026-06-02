import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.fetch_content import fetch_articles

def get_top_news():
    print("🔄 複数RSSフィードから最新ニュースを取得中...\n")
    articles = fetch_articles(max_per_feed=3)

    news_list = []
    for article in articles[:3]:
        news_list.append({
            "source": article["source"],
            "title": article["title"],
            "link": article["link"],
        })

    return news_list

if __name__ == "__main__":
    news = get_top_news()
    for i, item in enumerate(news, 1):
        print(f"【ニュース {i}】")
        print(f"ソース: {item['source']}")
        print(f"タイトル: {item['title']}")
        print(f"リンク: {item['link']}")
        print("-" * 40)
