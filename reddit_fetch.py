import requests
from datetime import datetime, timezone


def fetch_reddit_news(subreddit="sysadmin", limit=10):
    headers = {"User-Agent": "Reddit IT News Fetcher"}
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    posts = data["data"]["children"]
    news_items = []
    for post in posts:
        p_data = post["data"]

        # 1. Map to Nexthink Schema
        # 2. convert Unix timestamp to ISO 8601 (RFC 3339)
        published_at = datetime.fromtimestamp(
            p_data["created_utc"], tz=timezone.utc).isoformat().replace("+00:00", "Z")

        item = {
            "id": p_data["name"],
            "source": "reddit",
            "title": p_data['title'],
            "body": p_data.get('selftext', ''),
            "published_at": published_at,
        }
        news_items.append(item)
    return news_items


if __name__ == "__main__":
    news = fetch_reddit_news()
    for item in news:
        print(item)
