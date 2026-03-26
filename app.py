from preprocess import build_rule_text
from scorer import score_article
from rules import matches_discard_rule
from ranking import rank_articles
from models import NewsEntry
from embeddings import EmbeddingService
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


class NewsTriageService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    def process_articles(self, articles: list[NewsEntry]) -> list:
        now = datetime.now(timezone.utc)
        kept = []

        for article in articles:
            rule_text = build_rule_text(article)

            if matches_discard_rule(rule_text):
                # Discard immediately if it matches any discard rule
                continue

            scored = score_article(
                article=article,
                embedding_service=self.embedding_service,
                now=now,
            )

            if scored.keep:
                kept.append(scored)

        ranked = rank_articles(kept)
        return ranked


if __name__ == "__main__":
    sample_articles = [
        NewsEntry(
            id="1",
            source="reddit",
            title="Microsoft outage affects authentication across multiple tenants",
            body="Users report sign-in failures and service disruption across several enterprise tenants.",
            published_at="2026-03-26T08:00:00Z",
        ),
        NewsEntry(
            id="2",
            source="ars-technica",
            title="Best laptop for college in 2026",
            body="A full buying guide for students looking for a powerful but affordable laptop.",
            published_at="2026-03-25T10:00:00Z",
        ),
    ]

    service = NewsTriageService()
    results = service.process_articles(sample_articles)

    for item in results:
        print(item.model_dump())
