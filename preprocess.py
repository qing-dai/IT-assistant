import re

from config import MAX_BODY_CHARS_EMBEDDING, MAX_BODY_CHARS_LEXICAL
from models import NewsEntry


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_rule_text(article: NewsEntry) -> str:
    title = (article.title or "").strip()
    body = (article.body or "").strip()[:MAX_BODY_CHARS_LEXICAL]

    if title and body:
        return f"{title}. {body}"
    return title or body


def build_embedding_text(article: NewsEntry) -> str:
    title = (article.title or "").strip()
    body = (article.body or "").strip()[:MAX_BODY_CHARS_EMBEDDING]

    if title and body:
        return f"{title}. {body}"
    return title or body


def build_title_text(article: NewsEntry) -> str:
    return (article.title or "").strip()
