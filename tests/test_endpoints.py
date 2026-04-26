"""
tests/test_endpoints.py — API contract tests for /ingest and /retrieve.

Uses FastAPI's TestClient with mocked IngestService and DB so no OpenAI
calls or real database writes happen during testing.
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

os.environ["ENABLE_BACKGROUND_FETCH"] = "false"


VALID_BATCH = [
    {
        "id": "test-001",
        "source": "reddit",
        "title": "Critical zero-day in Windows actively exploited in the wild",
        "body": "Microsoft confirms RCE vulnerability affecting all Windows versions.",
        "published_at": "2026-03-29T10:00:00Z",
    },
    {
        "id": "test-002",
        "source": "ars-technica",
        "title": "Best mechanical keyboards for 2026",
        "body": "A buying guide for enthusiasts.",
        "published_at": "2026-03-29T09:00:00Z",
    },
]


@pytest.fixture(scope="module")
def client():
    mock_service = MagicMock()
    mock_service.process_articles.return_value = []

    with patch("controllers.api.IngestService", return_value=mock_service), \
         patch("controllers.api.init_db"), \
         patch("controllers.api.asyncio.create_task"), \
         patch("services.retrieve_service.get_filtered_items", return_value=[]), \
         patch("services.retrieve_service.get_latest_run_items", return_value=[]):
        from controllers.api import app
        with TestClient(app) as c:
            yield c


# --- POST /ingest ---

def test_ingest_valid_batch_returns_200(client):
    response = client.post("/ingest", json=VALID_BATCH)
    assert response.status_code == 200


def test_ingest_response_shape(client):
    response = client.post("/ingest", json=VALID_BATCH)
    body = response.json()
    assert "status" in body
    assert "run_id" in body
    assert "ingested" in body
    assert "kept" in body


def test_ingest_reports_correct_ingested_count(client):
    response = client.post("/ingest", json=VALID_BATCH)
    assert response.json()["ingested"] == len(VALID_BATCH)


def test_ingest_empty_batch_returns_400(client):
    response = client.post("/ingest", json=[])
    assert response.status_code == 400


def test_ingest_missing_required_field_returns_422(client):
    bad_item = [{"source": "reddit", "title": "No ID or date"}]
    response = client.post("/ingest", json=bad_item)
    assert response.status_code == 422


def test_ingest_invalid_date_returns_422(client):
    bad_item = [{**VALID_BATCH[0], "published_at": "not-a-date"}]
    response = client.post("/ingest", json=bad_item)
    assert response.status_code == 422


# --- arbitrary source ---

def test_ingest_arbitrary_source_returns_200(client):
    batch = [{**VALID_BATCH[0], "id": "arb-001", "source": "hacker-news"}]
    response = client.post("/ingest", json=batch)
    assert response.status_code == 200


def test_ingest_arbitrary_source_response_shape(client):
    batch = [{**VALID_BATCH[0], "id": "arb-002", "source": "hacker-news"}]
    response = client.post("/ingest", json=batch)
    body = response.json()
    assert body["status"] == "ok"
    assert "run_id" in body
    assert body["ingested"] == 1


# --- GET /retrieve ---

def test_retrieve_returns_200(client):
    response = client.get("/retrieve")
    assert response.status_code == 200


def test_retrieve_returns_list(client):
    response = client.get("/retrieve")
    assert isinstance(response.json(), list)


def test_retrieve_item_shape(client):
    """Each item in /retrieve must have the required contract fields with correct types."""
    mock_service = MagicMock()
    mock_service.process_articles.return_value = []

    fake_item = {
        "id": "test-shape-001",
        "source": "reddit",
        "title": "Critical zero-day exploited in the wild",
        "body": "Details about the vulnerability.",
        "published_at": "2026-03-29T10:00:00Z",
    }

    with patch("services.retrieve_service.get_filtered_items", return_value=[fake_item]):
        response = client.get("/retrieve")

    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) == 1

    item = items[0]
    assert isinstance(item["id"], str)
    assert isinstance(item["source"], str)
    assert isinstance(item["title"], str)
    # body is optional — if present must be str or null
    assert "body" in item
    assert item["body"] is None or isinstance(item["body"], str)
    assert isinstance(item["published_at"], str)


def test_retrieve_item_has_no_extra_scoring_fields(client):
    """The /retrieve contract must not leak internal scoring fields."""
    fake_item = {
        "id": "test-shape-002",
        "source": "ars-technica",
        "title": "Security advisory issued",
        "body": None,
        "published_at": "2026-03-29T08:00:00Z",
    }

    with patch("services.retrieve_service.get_filtered_items", return_value=[fake_item]):
        response = client.get("/retrieve")

    item = response.json()[0]
    internal_fields = {"keep", "fused_score", "rank_score", "lexical_score",
                       "semantic_score", "freshness_score", "decision_source",
                       "llm_reason", "llm_relevance_score", "predicted_category"}
    assert not internal_fields.intersection(item.keys()), (
        f"Internal fields leaked into /retrieve response: {internal_fields.intersection(item.keys())}"
    )
