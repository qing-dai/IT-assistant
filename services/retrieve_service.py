"""
services/retrieve_service.py — Read-side service for the triage pipeline.

Provides access to filtered (kept) articles and debug scoring data
without any coupling to the ingest pipeline.
"""
from data.db import get_filtered_items, get_filtered_items_full, get_latest_run_items


class RetrieveService:
    def get_filtered(self) -> list[dict]:
        """Return kept articles in the contract shape (id, source, title, body, published_at)."""
        return get_filtered_items()

    def get_filtered_full(self) -> list[dict]:
        """Return kept articles with all scoring fields, for internal dashboard use."""
        return get_filtered_items_full()

    def get_debug_items(self) -> list[dict]:
        """Return all articles from the latest run (kept + discarded) for debugging."""
        return get_latest_run_items()
