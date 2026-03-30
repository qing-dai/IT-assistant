import re

from models import NewsEntry


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def build_article_text(article: NewsEntry, max_body_chars: int = 0) -> str:
    """Combine title and body into a single string for scoring/rules/embedding.

    *max_body_chars* truncates the body before joining (0 = no truncation).
    """
    title = (article.title or "").strip()
    body = (article.body or "").strip()
    if max_body_chars > 0:
        body = body[:max_body_chars]

    if title and body:
        return f"{title}. {body}"
    return title or body


def build_title_text(article: NewsEntry) -> str:
    return (article.title or "").strip()
