"""
services/retrieve_service.py — Read-side service for the triage pipeline.

Provides access to filtered (kept) articles and debug scoring data
without any coupling to the ingest pipeline.
"""
from data.db import get_filtered_items, get_latest_run_items


class RetrieveService:
    def get_filtered(self) -> list[dict]:
        """Return kept articles sorted by rank (importance × recency)."""
        return get_filtered_items()

    def get_debug_items(self) -> list[dict]:
        """Return all articles from the latest run (kept + discarded) for debugging."""
        return get_latest_run_items()
