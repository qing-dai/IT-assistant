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
    severity_score: float
    entity_score: float
    freshness_score: float
    predicted_category: str
    rank_score: float = Field(default=0.0)
