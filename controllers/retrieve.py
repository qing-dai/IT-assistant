"""
controllers/retrieve.py — GET /retrieve and GET /debug/scoring controllers.

Thin HTTP layer: delegate to RetrieveService, return JSON responses.
"""
import asyncio
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.retrieve_service import RetrieveService

logger = logging.getLogger(__name__)

router = APIRouter()

_service = RetrieveService()


@router.get("/retrieve", summary="Retrieve filtered and ranked news events")
async def retrieve() -> JSONResponse:
    """
    Return all events the system decided to keep, sorted by rank
    (importance × recency). Deterministic for a given ingestion batch.

    Response shape matches the ingest contract, enriched with scoring fields.
    """
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, _service.get_filtered)
    logger.debug(f"Retrieve: returning {len(items)} kept items")
    return JSONResponse(content=items)


@router.get("/debug/scoring", summary="Scoring debug: all articles from latest run (kept + discarded)")
async def debug_scoring() -> JSONResponse:
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(None, _service.get_debug_items)
    return JSONResponse(content=items)
