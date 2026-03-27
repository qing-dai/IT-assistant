import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException

from app import NewsTriageService
from models import NewsEntry

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared service instance injected at startup via set_service().
_service: NewsTriageService | None = None


def set_service(service: NewsTriageService) -> None:
    global _service
    _service = service


@router.post("/ingest", summary="Ingest a batch of raw news events")
async def ingest(items: list[NewsEntry]) -> dict:
    """
    Accept a JSON array of raw event objects and run them through the triage
    pipeline. Returns an acknowledgment with counts.

    Required fields per item: id, source, title, published_at (ISO 8601 UTC).
    Optional: body.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Batch must not be empty.")
    if _service is None:
        raise HTTPException(status_code=503, detail="Service not ready yet.")

    run_id = str(uuid.uuid4())
    logger.info(f"Ingest: run_id={run_id} batch_size={len(items)}")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None, lambda: _service.process_articles(items, run_id)
    )

    logger.info(f"Ingest complete: run_id={run_id} kept={len(results)}/{len(items)}")
    return {
        "status": "ok",
        "run_id": run_id,
        "ingested": len(items),
        "kept": len(results),
    }
