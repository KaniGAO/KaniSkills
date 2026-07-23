"""NewsAPI 全球新闻聚合"""
import requests
from datetime import datetime, timedelta, timezone
from config import Config


# 宏观经济相关关键词
MACRO_QUERIES = [
    "markets economy",
    "central bank interest rates",
    "Federal Reserve ECB BOJ",
    "inflation GDP employment",
    "trade tariffs geopolitics",
    "treasury bonds yields",
    "commodities oil gold",
]


def fetch_macro_news() -> list[dict]:
    """获取宏观经济相关新闻"""
    if not Config.NEWSAPI_KEY or Config.NEWSAPI_KEY == "YOUR_NEWSAPI_KEY":
        print("  [NewsAPI] No API key configured")
        return []

    today = datetime.now(timezone.utc)
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")

    all_articles = []
    seen_urls = set()

    for query in MACRO_QUERIES:
        url = (
            f"https://newsapi.org/v2/everything"
            f"?q={query}&from={week_ago}&language=en"
            f"&sortBy=publishedAt&pageSize=20"
            f"&apiKey={Config.NEWSAPI_KEY}"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            articles = data.get("articles", [])
            
            for article in articles:
                article_url = (article.get("url") or "").strip()
                if not article_url or article_url in seen_urls:
                    continue
                seen_urls.add(article_url)

                source_name = ""
                if article.get("source"):
                    source_name = article["source"].get("name", "")

                pub_date = (article.get("publishedAt") or "")[:10]

                all_articles.append({
                    "title": (article.get("title") or "").strip(),
                    "description": (article.get("description") or "").strip()[:300],
                    "url": article_url,
                    "source": source_name or "NewsAPI",
                    "date": pub_date,
                })

        except requests.RequestException as e:
            print(f"  [NewsAPI] Error fetching '{query}': {e}")

    return all_articles[:25]
