import re
from typing import List

from rank_bm25 import BM25Okapi

from config import BM25_MAX_SCORE, BM25_QUERY_TERMS
from models import NewsEntry
from preprocess import build_article_text


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split()


class BatchBM25Scorer:
    def __init__(self, articles: List[NewsEntry]) -> None:
        self.articles = articles
        self.corpus_tokens = [
            tokenize(build_article_text(article, max_body_chars=1500))
            for article in articles
        ]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def get_raw_scores(self) -> List[float]:
        scores = self.bm25.get_scores(BM25_QUERY_TERMS)
        return [float(score) for score in scores]

    def get_normalized_scores(self) -> List[float]:
        raw_scores = self.get_raw_scores()
        return [min(score / BM25_MAX_SCORE, 1.0) for score in raw_scores]
