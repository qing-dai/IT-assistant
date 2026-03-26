from datetime import datetime, timezone

from config import (
    HARD_KEEP_BOOST,
    KEEP_THRESHOLD,
    LEXICAL_KEYWORDS,
    SEVERITY_TERMS,
    TITLE_KEEP_BOOST,
    VENDOR_TERMS,
    ScoringWeights,
)
from embeddings import EmbeddingService
from models import NewsEntry, ScoredNewsEntry
from preprocess import build_embedding_text, build_rule_text, build_title_text, normalize_text
from rules import matches_keep_rule, matches_keep_rule_in_title


def compute_lexical_score(text: str) -> float:
    normalized = normalize_text(text)
    raw = sum(weight for keyword, weight in LEXICAL_KEYWORDS.items()
              if keyword in normalized)
    return min(raw / 4.0, 1.0)


def compute_severity_score(text: str) -> float:
    normalized = normalize_text(text)
    raw = sum(weight for term, weight in SEVERITY_TERMS.items()
              if term in normalized)
    return min(raw / 2.5, 1.0)


def compute_entity_score(text: str) -> float:
    normalized = normalize_text(text)
    raw = max((weight for term, weight in VENDOR_TERMS.items()
              if term in normalized), default=0.0)
    return raw


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
    embedding_service: EmbeddingService,
    now: datetime,
    weights: ScoringWeights = ScoringWeights(),
) -> ScoredNewsEntry:
    rule_text = build_rule_text(article)
    embedding_text = build_embedding_text(article)
    title_text = build_title_text(article)

    hard_keep = matches_keep_rule(rule_text)
    title_keep = matches_keep_rule_in_title(title_text)

    lexical_score = compute_lexical_score(rule_text)
    semantic_score, predicted_category = embedding_service.compute_category_score(
        embedding_text)
    severity_score = compute_severity_score(rule_text)
    entity_score = compute_entity_score(rule_text)
    freshness_score = compute_freshness_score(article.published_at, now)

    final_score = (
        weights.lexical * lexical_score
        + weights.semantic * semantic_score
        + weights.severity * severity_score
        + weights.entity * entity_score
        + weights.freshness * freshness_score
    )

    if hard_keep:
        final_score += HARD_KEEP_BOOST

    if title_keep:
        final_score += TITLE_KEEP_BOOST

    final_score = min(final_score, 1.0)
    keep = final_score >= KEEP_THRESHOLD

    return ScoredNewsEntry(
        id=article.id,
        source=article.source,
        title=article.title,
        body=article.body,
        published_at=article.published_at,
        keep=keep,
        final_score=final_score,
        lexical_score=lexical_score,
        semantic_score=semantic_score,
        severity_score=severity_score,
        entity_score=entity_score,
        freshness_score=freshness_score,
        predicted_category=predicted_category,
    )
