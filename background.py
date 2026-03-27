"""
background.py — periodic news fetch from Reddit and Ars Technica.

Runs as an asyncio background task started by the FastAPI lifespan.
Skips articles already present in the database to avoid re-scoring.
"""
import asyncio
import logging
import os
import uuid

from app import NewsTriageService
from ars_it import fetch_ars_news
from db import get_existing_ids
from models import NewsEntry
from reddit_fetch import fetch_reddit_news

logger = logging.getLogger(__name__)

FETCH_INTERVAL_SEC = int(os.getenv("FETCH_INTERVAL_MINUTES", "10")) * 60
REDDIT_SUBREDDIT   = os.getenv("REDDIT_SUBREDDIT", "sysadmin")
REDDIT_LIMIT       = int(os.getenv("REDDIT_LIMIT", "25"))
ARS_LIMIT          = int(os.getenv("ARS_LIMIT", "20"))


async def run_fetch_cycle(service: NewsTriageService) -> None:
    """Fetch from all sources, skip seen IDs, triage novel articles."""
    loop = asyncio.get_event_loop()
    logger.info("Background fetch cycle starting…")

    # --- Reddit ---------------------------------------------------------
    try:
        raw_reddit = await loop.run_in_executor(
            None,
            lambda: fetch_reddit_news(subreddit=REDDIT_SUBREDDIT, limit=REDDIT_LIMIT),
        )
        logger.info(f"Reddit: fetched {len(raw_reddit)} posts from r/{REDDIT_SUBREDDIT}")
    except Exception as exc:
        logger.error(f"Reddit fetch failed: {exc}")
        raw_reddit = []

    # --- Ars Technica ---------------------------------------------------
    try:
        raw_ars = await loop.run_in_executor(
            None,
            lambda: fetch_ars_news(limit=ARS_LIMIT),
        )
        logger.info(f"Ars Technica: fetched {len(raw_ars)} articles")
    except Exception as exc:
        logger.error(f"Ars Technica fetch failed: {exc}")
        raw_ars = []

    # --- Deduplicate against DB ----------------------------------------
    raw_all = raw_reddit + raw_ars
    if not raw_all:
        logger.warning("Background fetch: no articles retrieved from any source.")
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

    # --- Triage --------------------------------------------------------
    articles = [NewsEntry(**item) for item in novel]
    run_id = str(uuid.uuid4())
    results = await loop.run_in_executor(
        None, lambda: service.process_articles(articles, run_id)
    )
    logger.info(
        f"Background fetch complete: run_id={run_id} "
        f"triaged={len(articles)} kept={len(results)}"
    )


async def background_fetch_loop(service: NewsTriageService) -> None:
    """
    Loop indefinitely: wait a short startup delay, then fetch on every
    FETCH_INTERVAL_SEC interval.
    """
    # Small startup delay so embeddings / DB are fully ready.
    await asyncio.sleep(5)
    while True:
        try:
            await run_fetch_cycle(service)
        except Exception as exc:
            logger.error(f"Unhandled error in fetch cycle: {exc}", exc_info=True)
        logger.info(f"Next background fetch in {FETCH_INTERVAL_SEC // 60} minute(s).")
        await asyncio.sleep(FETCH_INTERVAL_SEC)
