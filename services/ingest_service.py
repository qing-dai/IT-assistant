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
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    def _run_llm_judge(self, scored, article) -> tuple:
        """Call LLM judge for a single article. Returns (scored, llm_result)."""
        logger.info(f"LLM judge '{article.title}' fused={scored.fused_score:.3f}")
        start_time = datetime.now()
        llm_result = self.llm_judge.judge(
            source=article.source,
            title=article.title,
            body=article.body or "",
            fused_score=scored.fused_score,
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"LLM judgment done in {elapsed:.2f}s — '{article.title}'")
        return scored, llm_result

    def process_articles(self, articles: list[NewsEntry], run_id: str, persist: bool = True) -> list:
        now = datetime.now(timezone.utc)
        retrieved_at = now.isoformat().replace("+00:00", "Z")

        bm25_scorer = BatchBM25Scorer(articles)
        lexical_scores = bm25_scorer.get_normalized_scores()

        # Pass 1: score all articles, separate LLM candidates
        all_results = []
        llm_candidates = []  # list of (idx, scored, article)

        for idx, article in enumerate(articles):
            scored = score_article(
                article=article,
                lexical_score=lexical_scores[idx],
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
                llm_candidates.append((idx, scored, article))

            all_results.append(scored)

        # Pass 2: run all LLM calls concurrently
        if llm_candidates:
            logger.info(f"Running {len(llm_candidates)} LLM judge calls concurrently...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(self._run_llm_judge, scored, article): idx
                    for idx, scored, article in llm_candidates
                }
                for future in as_completed(futures):
                    scored, llm_result = future.result()
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
            for scored in all_results:
                insert_triage_result(scored, run_id=run_id, retrieved_at=retrieved_at)

        kept = [item for item in all_results if item.keep]
        ranked = rank_articles(kept)
        self._last_all_results = all_results  # available for evaluation, not used in production

        n_auto_keep    = sum(1 for r in all_results if r.decision_source == "auto_keep")
        n_llm_kept     = sum(1 for r in all_results if r.decision_source == "llm_judge" and r.keep)
        n_llm_discarded = sum(1 for r in all_results if r.decision_source == "llm_judge" and not r.keep)
        n_auto_discard = sum(1 for r in all_results if r.decision_source == "auto_discard")
        logger.info(
            f"Batch complete run_id={run_id}: "
            f"{len(articles)} in → "
            f"{n_auto_keep} auto_keep, "
            f"{n_llm_kept} llm_kept, "
            f"{n_llm_discarded} llm_discarded, "
            f"{n_auto_discard} auto_discard → "
            f"{len(kept)} kept"
        )
        return ranked
