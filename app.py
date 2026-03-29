from scorer import score_article
from ranking import compute_rank_score, rank_articles
from models import NewsEntry
from embeddings import EmbeddingService
from datetime import datetime, timezone
import uuid
from db import init_db, insert_triage_result
from bm25_scorer import BatchBM25Scorer
from llm_judge import LLMJudge
from config import AUTO_DISCARD_THRESHOLD, AUTO_KEEP_THRESHOLD, LLM_RELEVANCE_MIN
from dotenv import load_dotenv

load_dotenv()


class NewsTriageService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.llm_judge = LLMJudge()

    def process_articles(self, articles: list[NewsEntry], run_id: str, persist: bool = True) -> list:
        now = datetime.now(timezone.utc)
        retrieved_at = now.isoformat().replace("+00:00", "Z")
        all_results = []

        bm25_scorer = BatchBM25Scorer(articles)
        lexical_scores = bm25_scorer.get_normalized_scores()

        for idx, article in enumerate(articles):
            lexical_score = lexical_scores[idx]

            scored = score_article(
                article=article,
                lexical_score=lexical_score,
                embedding_service=self.embedding_service,
                now=now,
            )

            fused_score = scored.fused_score

            if fused_score < AUTO_DISCARD_THRESHOLD:
                print(
                    f"Auto-discarding article '{article.title}' with fused score {fused_score:.3f}")
                scored.keep = False
                scored.final_score = fused_score
                scored.decision_source = "auto_discard"
                scored.rank_score = 0.0

            elif fused_score >= AUTO_KEEP_THRESHOLD:
                print(
                    f"Auto-keeping article '{article.title}' with fused score {fused_score:.3f}")
                scored.keep = True
                scored.final_score = fused_score
                scored.decision_source = "auto_keep"
                scored.rank_score = compute_rank_score(scored)

            else:
                print(
                    f"Sending article '{article.title}' for LLM judgment with fused score {fused_score:.3f}")
                start_time = datetime.now()
                llm_result = self.llm_judge.judge(
                    source=article.source,
                    title=article.title,
                    body=article.body or "",
                    fused_score=fused_score,
                )
                end_time = datetime.now()
                print(
                    f"LLM judgment completed in {(end_time - start_time).total_seconds():.2f} seconds")

                scored.llm_reason = llm_result["reason"]
                scored.llm_relevance_score = llm_result["relevance_score"]
                scored.final_score = llm_result["normalized_score"]
                scored.decision_source = "llm_judge"

                if llm_result["keep"] and llm_result["relevance_score"] >= LLM_RELEVANCE_MIN:
                    scored.keep = True
                    scored.rank_score = compute_rank_score(scored)
                else:
                    scored.keep = False
                    scored.rank_score = 0.0

            if persist:
                insert_triage_result(scored, run_id=run_id,
                                     retrieved_at=retrieved_at)
            all_results.append(scored)

        kept = [item for item in all_results if item.keep]
        ranked = rank_articles(kept)
        self._last_all_results = all_results  # available for evaluation, not used in production
        return ranked


if __name__ == "__main__":
    from sources import SOURCES

    init_db()
    raw_articles = []
    for source in SOURCES:
        print(f"Fetching from {source.source_id}...")
        raw_articles.extend(source.fetch(limit=20))

    print(f"Fetched {len(raw_articles)} articles total. Processing...")
    articles = [NewsEntry(**item) for item in raw_articles]

    run_id = str(uuid.uuid4())
    service = NewsTriageService()
    results = service.process_articles(articles, run_id=run_id)
    print(f"Kept {len(results)} articles after triage. Ranked results:")

    for item in results:
        print(item.model_dump())
