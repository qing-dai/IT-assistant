from datetime import datetime, timezone

from config import (
    HARD_KEEP_BOOST,
    ScoringWeights,
)
from embeddings import EmbeddingService
from models import NewsEntry, ScoredNewsEntry
from preprocess import build_article_text
from rules import matches_keep_rule


def compute_freshness_score(published_at: datetime, now: datetime) -> float:
    # Ensure both datetimes are standard timezone-aware for accurate comparison
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_hours = max((now - published_at).total_seconds() / 3600.0, 0.0)
    # Articles older than 7 days (168 hours) get a freshness score of 0,
    # newer articles get a score between 0 and 1, higher for fresher articles.xs
    return max(0.0, 1.0 - min(age_hours / 168.0, 1.0))


def score_article(
    article: NewsEntry,
    lexical_score: float,
    embedding_service: EmbeddingService,
    now: datetime,
    weights: ScoringWeights = ScoringWeights(),
) -> ScoredNewsEntry:
    rule_text = build_article_text(article)
    embedding_text = build_article_text(article)

    hard_keep = matches_keep_rule(rule_text)

    semantic_score, predicted_category = embedding_service.compute_category_score(
        embedding_text)
    freshness_score = compute_freshness_score(article.published_at, now)

    fused_score = (
        weights.lexical * lexical_score
        + weights.semantic * semantic_score
        + weights.freshness * freshness_score
    )

    if hard_keep:
        fused_score += HARD_KEEP_BOOST

    fused_score = min(fused_score, 1.0)

    return ScoredNewsEntry(
        id=article.id,
        source=article.source,
        title=article.title,
        body=article.body,
        published_at=article.published_at,
        keep=False,
        final_score=fused_score,
        lexical_score=lexical_score,
        semantic_score=semantic_score,
        freshness_score=freshness_score,
        predicted_category=predicted_category,
        fused_score=fused_score,
        decision_source="",
        llm_reason="",
        llm_relevance_score=0.0,
    )
