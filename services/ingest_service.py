"""
services/ingest_service.py — Core triage pipeline for ingested news articles.

Responsibilities:
  - Score each article (lexical, semantic, freshness → fused score)
  - Gate on thresholds: auto-discard / LLM judge / auto-keep
  - Persist results to the database
  - Return ranked kept articles
"""
import logging
import uuid
from datetime import datetime, timezone

from config import AUTO_DISCARD_THRESHOLD, AUTO_KEEP_THRESHOLD, LLM_RELEVANCE_MIN
from data.db import insert_triage_result
from models import NewsEntry
from tools.bm25_scorer import BatchBM25Scorer
from tools.embeddings import EmbeddingService
from tools.llm_judge import LLMJudge
from tools.ranking import compute_rank_score, rank_articles
from tools.scorer import score_article

logger = logging.getLogger(__name__)


class IngestService:
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
                logger.info(f"Auto-discard '{article.title}' fused={fused_score:.3f}")
                scored.keep = False
                scored.final_score = fused_score
                scored.decision_source = "auto_discard"
                scored.rank_score = 0.0

            elif fused_score >= AUTO_KEEP_THRESHOLD:
                logger.info(f"Auto-keep '{article.title}' fused={fused_score:.3f}")
                scored.keep = True
                scored.final_score = fused_score
                scored.decision_source = "auto_keep"
                scored.rank_score = compute_rank_score(scored)

            else:
                logger.info(f"LLM judge '{article.title}' fused={fused_score:.3f}")
                start_time = datetime.now()
                llm_result = self.llm_judge.judge(
                    source=article.source,
                    title=article.title,
                    body=article.body or "",
                    fused_score=fused_score,
                )
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"LLM judgment done in {elapsed:.2f}s")

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
                insert_triage_result(scored, run_id=run_id, retrieved_at=retrieved_at)
            all_results.append(scored)

        kept = [item for item in all_results if item.keep]
        ranked = rank_articles(kept)
        self._last_all_results = all_results  # available for evaluation, not used in production
        return ranked
