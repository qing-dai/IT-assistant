import re
from typing import List

from rank_bm25 import BM25Okapi

from config import BM25_MAX_SCORE, BM25_QUERY_TERMS
from models import NewsEntry


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split()


def build_bm25_text(article: NewsEntry, max_body_chars: int = 1500) -> str:
    title = (article.title or "").strip()
    body = (article.body or "").strip()[:max_body_chars]

    if title and body:
        return f"{title}. {body}"
    return title or body


class BatchBM25Scorer:
    def __init__(self, articles: List[NewsEntry]) -> None:
        self.articles = articles
        self.corpus_tokens = [
            tokenize(build_bm25_text(article))
            for article in articles
        ]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def get_raw_scores(self) -> List[float]:
        scores = self.bm25.get_scores(BM25_QUERY_TERMS)
        return [float(score) for score in scores]

    def get_normalized_scores(self) -> List[float]:
        raw_scores = self.get_raw_scores()
        return [min(score / BM25_MAX_SCORE, 1.0) for score in raw_scores]
