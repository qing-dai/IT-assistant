import feedparser
import requests  # Use requests to handle the header, then pass to feedparser
from datetime import datetime, timezone


def fetch_ars_news():
    url = "https://feeds.arstechnica.com/arstechnica/index"
    headers = {'User-Agent': 'NexthinkAssignmentBot/1.0'}

    try:
        # Fetching content with a header first is more reliable in 2026
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse the raw content
        feed = feedparser.parse(response.content)

        if feed.bozo:
            # Print the specific error for debugging
            print(f"Detail: {feed.bozo_exception}")
            return []

        articles = []
        for entry in feed.entries[:20]:
            # Convert the published_parsed tuple to a UTC ISO string
            published_at = datetime(
                *entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

            articles.append({
                "id": entry.id,
                "source": "ars-technica",
                "title": entry.title,
                # description ==> summary in feedparser
                # content ==> content in feedparser.
                # for our case, we test with summary, as in real-time news systems, summary is enough to bug detection
                "body": entry.summary,
                "published_at": published_at
            })
        return articles

    except Exception as e:
        print(f"Failed to fetch Ars Technica: {e}")
        return []


if __name__ == "__main__":
    data = fetch_ars_news()
    for item in data:
        print(item)
