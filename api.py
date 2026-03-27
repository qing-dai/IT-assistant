"""
api.py — FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app
  - Lifespan: init DB, warm up the triage service, start/stop background fetch
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

from app import NewsTriageService
from background import background_fetch_loop
from db import init_db
from routers import ingest as ingest_router
from routers import retrieve as retrieve_router
from routers.ingest import set_service

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("api")

ENABLE_BG_FETCH = os.getenv("ENABLE_BACKGROUND_FETCH", "true").lower() == "true"
STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialise the database
    init_db()

    # 2. Warm up the triage service (loads embedding model once)
    logger.info("Warming up NewsTriageService…")
    service = NewsTriageService()
    set_service(service)  # share instance with the ingest router
    logger.info("NewsTriageService ready.")

    # 3. Optionally start the background fetch task
    bg_task = None
    if ENABLE_BG_FETCH:
        bg_task = asyncio.create_task(background_fetch_loop(service))
        logger.info("Background fetch task started.")
    else:
        logger.info("Background fetch disabled (ENABLE_BACKGROUND_FETCH != true).")

    yield

    # 4. Graceful shutdown
    if bg_task:
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass
        logger.info("Background fetch task stopped.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="IT Newsfeed Triage API",
    description=(
        "Real-time IT news aggregation, filtering, and ranking for IT managers. "
        "Exposes /ingest and /retrieve per the Nexthink mock-newsfeed contract."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# API routers
app.include_router(ingest_router.router)
app.include_router(retrieve_router.router)

# Serve static assets (dashboard.html + any future JS/CSS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def dashboard():
    """Serve the news feed dashboard."""
    return FileResponse(STATIC_DIR / "dashboard.html")


# ---------------------------------------------------------------------------
# Dev entry point:  python api.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
