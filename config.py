"""
config.py — App-wide settings: thresholds, weights, model names.

For expandable domain vocabulary (CATEGORY_PROTOTYPES, BM25_QUERY_TERMS,
KEEP_TERMS) see tools/vocabulary.py.
"""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ScoringWeights:
    lexical: float = 0.30
    semantic: float = 0.50
    # remove the weight of recency for fused score, as it is considered in the final ranking score
    freshness: float = 0.00


OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
LLM_JUDGE_MODEL = os.getenv("LLM_JUDGE_MODEL", "gpt-5")

BM25_MAX_SCORE = 8.0

KEEP_THRESHOLD = 0.58
HARD_KEEP_BOOST = 0.15

AUTO_DISCARD_THRESHOLD = 0.45   # below this → auto-discard (no LLM call)
AUTO_KEEP_THRESHOLD = 0.75      # at/above this → auto-keep (no LLM call)
LLM_RELEVANCE_MIN = 70          # minimum LLM relevance_score (0-100) to keep
