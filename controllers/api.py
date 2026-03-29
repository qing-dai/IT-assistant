"""
controllers/api.py — FastAPI application setup.

Responsibilities:
  - Create the FastAPI app
  - Lifespan: init DB, warm up services, start/stop background fetch
  - Mount routers and static files
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from controllers.ingest import router as ingest_router
from controllers.ingest import set_ingest_service
from controllers.retrieve import router as retrieve_router
from data.db import init_db
from services.background import background_fetch_loop
from services.ingest_service import IngestService

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("api")

ENABLE_BG_FETCH = os.getenv("ENABLE_BACKGROUND_FETCH", "true").lower() == "true"
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    logger.info("Warming up IngestService…")
    ingest_service = IngestService()
    set_ingest_service(ingest_service)
    logger.info("IngestService ready.")

    bg_task = None
    if ENABLE_BG_FETCH:
        bg_task = asyncio.create_task(background_fetch_loop(ingest_service))
        logger.info("Background fetch task started.")
    else:
        logger.info("Background fetch disabled (ENABLE_BACKGROUND_FETCH != true).")

    yield

    if bg_task:
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass
        logger.info("Background fetch task stopped.")


app = FastAPI(
    title="IT Newsfeed Triage API",
    description=(
        "Real-time IT news aggregation, filtering, and ranking for IT managers. "
        "Exposes /ingest and /retrieve per the Nexthink mock-newsfeed contract."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ingest_router)
app.include_router(retrieve_router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the news feed dashboard."""
    return FileResponse(STATIC_DIR / "dashboard.html")
