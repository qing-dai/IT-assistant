import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
from urllib.parse import urljoin, urldefrag

import requests
from bs4 import BeautifulSoup


BASE_SECTION_URL = "https://arstechnica.com/security/"
HEADERS = {"User-Agent": "NexthinkAssignmentBot/1.0"}
REQUEST_TIMEOUT = 15
MAX_BODY_CHARS = 2000


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def is_article_url(url: str) -> bool:
    if not url.startswith("https://arstechnica.com/security/"):
        return False

    if "/page/" in url:
        return False

    return bool(re.search(r"/\d{4}/\d{2}/", url))


def extract_article_links(listing_html: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "html.parser")
    urls = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        full_url = urljoin(BASE_SECTION_URL, href)
        full_url, _ = urldefrag(full_url)
        if is_article_url(full_url):
            urls.add(full_url)

    return list(urls)


def extract_summary_text(soup: BeautifulSoup) -> str:
    meta_candidates = [
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ]

    for attrs in meta_candidates:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            text = tag["content"].strip()
            if text:
                return text

    return ""


def parse_published_at(soup: BeautifulSoup) -> str:
    time_tag = soup.find("time")
    if not time_tag:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # prefer machine-readable datetime attribute
    raw = time_tag.get("datetime")
    if raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_body_text(soup: BeautifulSoup) -> str:
    # common article body container patterns
    candidates = [
        soup.find("div", class_=re.compile(
            r"article-content|post-content|entry-content")),
        soup.find("section", class_=re.compile(
            r"article-content|post-content|entry-content")),
        soup.find("article"),
    ]

    text_parts = []

    for container in candidates:
        if not container:
            continue

        paragraphs = container.find_all("p")
        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            if text:
                text_parts.append(text)

        if text_parts:
            break

    body = " ".join(text_parts).strip()
    return body[:MAX_BODY_CHARS]


def parse_article(url: str) -> dict | None:
    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("h1")
        if not title_tag:
            return None

        title = title_tag.get_text(" ", strip=True)
        summary = extract_summary_text(soup)

        if not summary:
            summary = extract_body_text(soup)[:500]

        published_at = parse_published_at(soup)

        return {
            "id": url,
            "source": "ars-technica",
            "title": title,
            "body": summary,
            "published_at": published_at,
        }
    except Exception as e:
        print(f"Failed to parse article {url}: {e}")
        return None


def fetch_ars_news(limit: int = 100, max_pages: int = 10, sleep_sec: float = 0.5) -> list[dict]:
    article_urls: list[str] = []
    seen = set()

    for page_num in range(1, max_pages + 1):
        page_url = BASE_SECTION_URL if page_num == 1 else f"{BASE_SECTION_URL}page/{page_num}/"

        try:
            print(f"Fetching listing page: {page_url}")
            listing_html = fetch_html(page_url)
            links = extract_article_links(listing_html)

            for link in links:
                if link not in seen:
                    seen.add(link)
                    article_urls.append(link)

            print(f"Collected {len(article_urls)} unique article URLs so far.")

            if len(article_urls) >= limit:
                break

            time.sleep(sleep_sec)

        except Exception as e:
            print(f"Failed to fetch listing page {page_url}: {e}")
            break

    results = []
    for url in article_urls:
        item = parse_article(url)
        if item:
            results.append(item)
        time.sleep(sleep_sec)

    results.sort(key=lambda x: x["published_at"], reverse=True)
    return results[:limit]


if __name__ == "__main__":
    data = fetch_ars_news(limit=20, max_pages=12)
    print(f"Fetched {len(data)} Ars articles.")
    for item in data[:5]:
        print(item)
