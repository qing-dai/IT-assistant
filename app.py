from preprocess import build_rule_text
from scorer import score_article
from rules import matches_discard_rule
from ranking import compute_rank_score, rank_articles
from models import NewsEntry
from embeddings import EmbeddingService
from reddit_fetch import fetch_reddit_news
from datetime import datetime, timezone
import uuid
from db import init_db, insert_triage_result
from dotenv import load_dotenv

load_dotenv()


class NewsTriageService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    def process_articles(self, articles: list[NewsEntry], run_id: str) -> list:
        now = datetime.now(timezone.utc)
        retrieved_at = now.isoformat().replace("+00:00", "Z")
        all_results = []

        for article in articles:
            rule_text = build_rule_text(article)

            if matches_discard_rule(rule_text):
                scored = score_article(
                    article=article,
                    embedding_service=self.embedding_service,
                    now=now,
                )
                scored.keep = False
                scored.rank_score = 0.0
                insert_triage_result(scored, run_id=run_id,
                                     retrieved_at=retrieved_at)
                all_results.append(scored)
                continue

            scored = score_article(
                article=article,
                embedding_service=self.embedding_service,
                now=now,
            )

            scored.rank_score = compute_rank_score(scored)
            insert_triage_result(scored, run_id=run_id,
                                 retrieved_at=retrieved_at)
            all_results.append(scored)

        kept = [item for item in all_results if item.keep]
        ranked = rank_articles(kept)
        return ranked


if __name__ == "__main__":
    # sample_articles = [
    #     NewsEntry(
    #         id="1",
    #         source="reddit",
    #         title="Microsoft outage affects authentication across multiple tenants",
    #         body="Users report sign-in failures and service disruption across several enterprise tenants.",
    #         published_at="2026-03-26T08:00:00Z",
    #     ),
    #     NewsEntry(
    #         id="2",
    #         source="ars-technica",
    #         title="Best laptop for college in 2026",
    #         body="A full buying guide for students looking for a powerful but affordable laptop.",
    #         published_at="2026-03-25T10:00:00Z",
    #     ),
    # ]
    init_db()
    print("Fetching news from Reddit...")
    raw_articles = fetch_reddit_news(limit=200)
    print(f"Fetched {len(raw_articles)} articles. Processing...")
    sample_articles = [NewsEntry(**item) for item in raw_articles]
    print(f"Processing {len(sample_articles)} articles...")

    run_id = str(uuid.uuid4())
    service = NewsTriageService()
    results = service.process_articles(sample_articles, run_id=run_id)
    print(f"Kept {len(results)} articles after triage. Ranked results:")

    for item in results:
        print(item.model_dump())
