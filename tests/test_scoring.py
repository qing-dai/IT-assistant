"""
tests/test_scoring.py — Pure scoring function tests (no OpenAI calls).

Tests freshness decay and rank score computation in isolation.
"""
from datetime import datetime, timezone, timedelta

from models import ScoredNewsEntry
from tools.scorer import compute_freshness_score
from tools.ranking import compute_rank_score, rank_articles


def _make_scored(id: str, final_score: float, freshness_score: float, published_at: datetime) -> ScoredNewsEntry:
    return ScoredNewsEntry(
        id=id,
        source="reddit",
        title=f"Article {id}",
        published_at=published_at,
        keep=True,
        final_score=final_score,
        lexical_score=0.5,
        semantic_score=0.5,
        freshness_score=freshness_score,
        predicted_category="security_incident",
        fused_score=final_score,
        decision_source="auto_keep",
    )


# --- freshness ---

def test_fresh_article_scores_near_one():
    now = datetime.now(timezone.utc)
    score = compute_freshness_score(now, now)
    assert score == 1.0


def test_article_one_day_old():
    now = datetime.now(timezone.utc)
    published = now - timedelta(hours=24)
    score = compute_freshness_score(published, now)
    assert 0.8 < score < 0.9


def test_article_older_than_7_days_scores_zero():
    now = datetime.now(timezone.utc)
    published = now - timedelta(days=8)
    score = compute_freshness_score(published, now)
    assert score == 0.0


def test_future_article_scores_one():
    now = datetime.now(timezone.utc)
    published = now + timedelta(hours=1)
    score = compute_freshness_score(published, now)
    assert score == 1.0


# --- ranking ---

def test_rank_score_formula():
    now = datetime.now(timezone.utc)
    article = _make_scored("a", final_score=0.8, freshness_score=0.6, published_at=now)
    rank = compute_rank_score(article)
    assert abs(rank - (0.80 * 0.8 + 0.20 * 0.6)) < 1e-6


def test_rank_articles_sorted_by_rank_score():
    now = datetime.now(timezone.utc)
    low  = _make_scored("low",  final_score=0.5, freshness_score=0.4, published_at=now)
    high = _make_scored("high", final_score=0.9, freshness_score=0.9, published_at=now)
    mid  = _make_scored("mid",  final_score=0.7, freshness_score=0.6, published_at=now)

    ranked = rank_articles([low, high, mid])
    assert ranked[0].id == "high"
    assert ranked[-1].id == "low"
