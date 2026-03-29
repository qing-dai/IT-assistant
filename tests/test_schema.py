"""
tests/test_schema.py — Validate the NewsEntry contract.

Checks that the ingest schema accepts valid inputs and rejects
missing/malformed fields, matching the Nexthink API contract.
"""
import pytest
from pydantic import ValidationError

from models import NewsEntry


VALID_ITEM = {
    "id": "test-001",
    "source": "reddit",
    "title": "Critical zero-day actively exploited in Windows",
    "body": "Microsoft confirms RCE vulnerability affecting all versions.",
    "published_at": "2026-03-29T10:00:00Z",
}


def test_valid_entry():
    entry = NewsEntry(**VALID_ITEM)
    assert entry.id == "test-001"
    assert entry.source == "reddit"
    assert entry.title == "Critical zero-day actively exploited in Windows"


def test_body_is_optional():
    item = {k: v for k, v in VALID_ITEM.items() if k != "body"}
    entry = NewsEntry(**item)
    assert entry.body is None


def test_missing_id_raises():
    item = {k: v for k, v in VALID_ITEM.items() if k != "id"}
    with pytest.raises(ValidationError):
        NewsEntry(**item)


def test_missing_source_raises():
    item = {k: v for k, v in VALID_ITEM.items() if k != "source"}
    with pytest.raises(ValidationError):
        NewsEntry(**item)


def test_missing_title_raises():
    item = {k: v for k, v in VALID_ITEM.items() if k != "title"}
    with pytest.raises(ValidationError):
        NewsEntry(**item)


def test_missing_published_at_raises():
    item = {k: v for k, v in VALID_ITEM.items() if k != "published_at"}
    with pytest.raises(ValidationError):
        NewsEntry(**item)


def test_invalid_published_at_raises():
    item = {**VALID_ITEM, "published_at": "not-a-date"}
    with pytest.raises(ValidationError):
        NewsEntry(**item)
