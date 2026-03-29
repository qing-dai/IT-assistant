from models import ScoredNewsEntry


def compute_rank_score(article: ScoredNewsEntry) -> float:
    return 0.80 * article.final_score + 0.20 * article.freshness_score


def rank_articles(articles: list[ScoredNewsEntry]) -> list[ScoredNewsEntry]:
    for article in articles:
        article.rank_score = compute_rank_score(article)

    return sorted(
        articles,
        key=lambda x: (-x.rank_score, -x.published_at.timestamp(), x.id),
    )
