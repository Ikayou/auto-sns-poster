import feedparser

def get_top_news():
    # heise.de の公式RSSフィードURL
    rss_url = "https://www.heise.de/newsticker/heise-atom.xml"
    
    print(f"🔄 {rss_url} から最新ニュースを取得中...\n")
    feed = feedparser.parse(rss_url)
    
    news_list = []
    # 上から順に最新3件を取得
    for entry in feed.entries[:3]:
        title = entry.title
        link = entry.link
        
        news_list.append({
            "title": title,
            "link": link
        })
        
    return news_list

if __name__ == "__main__":
    news = get_top_news()
    for i, item in enumerate(news, 1):
        print(f"【ニュース {i}】")
        print(f"タイトル: {item['title']}")
        print(f"リンク: {item['link']}")
        print("-" * 40)