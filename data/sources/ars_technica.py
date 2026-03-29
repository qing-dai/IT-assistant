"""
data/sources/ars_technica.py — Ars Technica security news source.

Scrapes the /security/ section listing pages, then parses each article page for
title, body summary, and publication date.
"""
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urljoin, urldefrag

import requests
from bs4 import BeautifulSoup

from data.sources.base import NewsSource

logger = logging.getLogger(__name__)

BASE_SECTION_URL = "https://arstechnica.com/security/"
HEADERS = {"User-Agent": "NexthinkAssignmentBot/1.0"}
REQUEST_TIMEOUT = 15
MAX_BODY_CHARS = 2000


def _fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def _is_article_url(url: str) -> bool:
    if not url.startswith("https://arstechnica.com/security/"):
        return False
    if "/page/" in url:
        return False
    return bool(re.search(r"/\d{4}/\d{2}/", url))


def _extract_article_links(listing_html: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "html.parser")
    urls = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        full_url, _ = urldefrag(urljoin(BASE_SECTION_URL, href))
        if _is_article_url(full_url):
            urls.add(full_url)
    return list(urls)


def _extract_summary_text(soup: BeautifulSoup) -> str:
    for attrs in [
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            text = tag["content"].strip()
            if text:
                return text
    return ""


def _parse_published_at(soup: BeautifulSoup) -> str:
    time_tag = soup.find("time")
    if time_tag:
        raw = time_tag.get("datetime")
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                pass
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_body_text(soup: BeautifulSoup) -> str:
    candidates = [
        soup.find("div", class_=re.compile(r"article-content|post-content|entry-content")),
        soup.find("section", class_=re.compile(r"article-content|post-content|entry-content")),
        soup.find("article"),
    ]
    for container in candidates:
        if not container:
            continue
        paragraphs = container.find_all("p")
        text_parts = [p.get_text(" ", strip=True) for p in paragraphs if p.get_text(" ", strip=True)]
        if text_parts:
            return " ".join(text_parts)[:MAX_BODY_CHARS]
    return ""


def _parse_article(url: str) -> dict | None:
    try:
        html = _fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("h1")
        if not title_tag:
            return None

        title = title_tag.get_text(" ", strip=True)
        body = _extract_summary_text(soup) or _extract_body_text(soup)[:500]

        return {
            "id": url,
            "source": "ars-technica",
            "title": title,
            "body": body,
            "published_at": _parse_published_at(soup),
        }
    except Exception as exc:
        logger.warning(f"Failed to parse article {url}: {exc}")
        return None


class ArsTechnicaSource(NewsSource):
    source_id = "ars-technica"

    def __init__(self, max_pages: int = 10, sleep_sec: float = 0.5) -> None:
        self.max_pages = max_pages
        self.sleep_sec = sleep_sec

    def fetch(self, limit: int = 20) -> list[dict]:
        article_urls: list[str] = []
        seen: set[str] = set()

        for page_num in range(1, self.max_pages + 1):
            page_url = (
                BASE_SECTION_URL
                if page_num == 1
                else f"{BASE_SECTION_URL}page/{page_num}/"
            )
            try:
                logger.debug(f"Ars Technica: fetching listing page {page_url}")
                links = _extract_article_links(_fetch_html(page_url))
                for link in links:
                    if link not in seen:
                        seen.add(link)
                        article_urls.append(link)
                if len(article_urls) >= limit:
                    break
                time.sleep(self.sleep_sec)
            except Exception as exc:
                logger.error(f"Ars Technica: listing page failed {page_url}: {exc}")
                break

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_parse_article, url): url for url in article_urls[:limit]}
            results = []
            for future in as_completed(futures):
                item = future.result()
                if item:
                    results.append(item)

        results.sort(key=lambda x: x["published_at"], reverse=True)
        logger.info(f"Ars Technica: fetched {len(results)} articles")
        return results
