from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsEntry(BaseModel):
    id: str
    source: str
    title: str
    body: Optional[str] = None
    published_at: datetime


class ScoredNewsEntry(BaseModel):
    id: str
    source: str
    title: str
    body: Optional[str] = None
    published_at: datetime

    keep: bool
    final_score: float
    lexical_score: float
    semantic_score: float
    freshness_score: float
    predicted_category: str
    rank_score: float = Field(default=0.0)

    fused_score: float = 0.0
    decision_source: str = ""
    llm_reason: str = ""
    llm_relevance_score: float = 0.0


class LLMJudgeResult(BaseModel):
    keep: bool
    relevance_score: int = Field(ge=0, le=100)
    reason: str
