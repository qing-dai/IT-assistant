"""
services/background.py — Periodic news fetch from all registered sources.

Runs as an asyncio background task started by the FastAPI lifespan.
Skips articles already present in the database to avoid re-scoring.
"""
import asyncio
import logging
import os
import uuid

from data.db import get_existing_ids
from data.sources import SOURCES
from models import NewsEntry
from services.ingest_service import IngestService

logger = logging.getLogger(__name__)

FETCH_INTERVAL_SEC = int(os.getenv("FETCH_INTERVAL_MINUTES", "10")) * 60


async def run_fetch_cycle(service: IngestService) -> None:
    """Fetch from all registered sources, skip seen IDs, triage novel articles."""
    loop = asyncio.get_event_loop()
    logger.info("Background fetch cycle starting…")

    raw_all: list[dict] = []
    for source in SOURCES:
        try:
            items = await loop.run_in_executor(
                None, lambda s=source: s.fetch(limit=s.default_limit)
            )
            logger.info(f"{source.source_id}: fetched {len(items)} items")
            raw_all.extend(items)
        except Exception as exc:
            logger.error(f"{source.source_id} fetch failed: {exc}")

    if not raw_all:
        logger.warning(
            "Background fetch: no articles retrieved from any source.")
        return

    existing_ids = await loop.run_in_executor(None, get_existing_ids)
    novel = [item for item in raw_all if item["id"] not in existing_ids]

    logger.info(
        f"Background fetch: {len(raw_all)} total, "
        f"{len(raw_all) - len(novel)} already seen, "
        f"{len(novel)} new articles to triage."
    )
    if not novel:
        return

    articles = [NewsEntry(**item) for item in novel]
    run_id = str(uuid.uuid4())
    results = await loop.run_in_executor(
        None, lambda: service.process_articles(articles, run_id)
    )
    logger.info(
        f"Background fetch complete: run_id={run_id} "
        f"triaged={len(articles)} kept={len(results)}"
    )


async def background_fetch_loop(service: IngestService) -> None:
    """Loop indefinitely: short startup delay, then fetch every FETCH_INTERVAL_SEC."""
    await asyncio.sleep(5)  # wait for 5s for db and ingest service to be ready
    while True:
        try:
            await run_fetch_cycle(service)
        except Exception as exc:
            logger.error(
                f"Unhandled error in fetch cycle: {exc}", exc_info=True)
        logger.info(
            f"Next background fetch in {FETCH_INTERVAL_SEC // 60} minute(s).")
        await asyncio.sleep(FETCH_INTERVAL_SEC)
