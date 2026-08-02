"""Finnhub 市场新闻采集"""
import requests
from datetime import datetime, timezone

from config import Config


def fetch_market_news() -> list[dict]:
    """获取 Finnhub 通用市场新闻"""
    url = f"https://finnhub.io/api/v1/news?category=general&token={Config.FINNHUB_API_KEY}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"  [Finnhub] API error: {resp.status_code} {resp.text[:100]}")
            return []
        data = resp.json()
        if not isinstance(data, list):
            return []

        normalized = []
        seen_urls = set()
        for item in data:
            url = (item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            
            ts = item.get("datetime", 0)
            try:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                date_str = ""

            normalized.append({
                "title": (item.get("headline") or item.get("title") or "").strip(),
                "summary": (item.get("summary") or "").strip()[:300],
                "url": url,
                "source": "Finnhub",
                "category": (item.get("category") or "").strip(),
                "date": date_str,
                "related": (item.get("related") or "").strip(),
            })

        return normalized[:25]  # Dify兼容限制
    except requests.RequestException as e:
        print(f"  [Finnhub] Request failed: {e}")
        return []


def fetch_company_news(symbols: list[str] = None) -> list[dict]:
    """获取特定公司新闻"""
    if not symbols:
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "JPM", "GS"]
    
    all_news = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    for sym in symbols:
        url = f"https://finnhub.io/api/v1/company-news?symbol={sym}&from={today}&to={today}&token={Config.FINNHUB_API_KEY}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data[:3]:
                        all_news.append({
                            "title": (item.get("headline") or "").strip(),
                            "summary": (item.get("summary") or "").strip()[:200],
                            "url": (item.get("url") or "").strip(),
                            "source": f"Finnhub/{sym}",
                            "date": today,
                        })
        except Exception:
            pass
    
    return all_news
