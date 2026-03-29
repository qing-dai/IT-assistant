"""
data/sources/reddit.py — Reddit news source.

Fetches posts from a configurable subreddit via the public JSON API.
"""
import logging
from datetime import datetime, timezone

import requests

from data.sources.base import NewsSource

logger = logging.getLogger(__name__)


class RedditSource(NewsSource):
    source_id = "reddit"

    def __init__(self, subreddit: str = "sysadmin") -> None:
        self.subreddit = subreddit

    def fetch(self, limit: int = 25) -> list[dict]:
        url = f"https://www.reddit.com/r/{self.subreddit}/new.json?limit={limit}"
        headers = {"User-Agent": "NexthinkAssignmentBot/1.0"}

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        posts = response.json()["data"]["children"]
        items = []
        for post in posts:
            p = post["data"]
            published_at = (
                datetime.fromtimestamp(p["created_utc"], tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
            items.append({
                "id": p["name"],
                "source": self.source_id,
                "title": p["title"],
                "body": p.get("selftext", ""),
                "published_at": published_at,
            })

        logger.info(f"Reddit r/{self.subreddit}: fetched {len(items)} posts")
        return items
