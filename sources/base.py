"""
sources/base.py — Abstract base class for all news sources.

Adding a new source: subclass NewsSource, implement fetch(), and register the
instance in sources/__init__.py.  No other files need to change.
"""
from abc import ABC, abstractmethod


class NewsSource(ABC):
    """Contract every news source must satisfy."""

    #: Unique source identifier used in the NewsEntry.source field.
    source_id: str

    @abstractmethod
    def fetch(self, limit: int) -> list[dict]:
        """
        Fetch up to *limit* articles and return them as dicts that match the
        NewsEntry schema: id, source, title, body (optional), published_at.
        """
        ...
