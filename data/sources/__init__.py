"""
data/sources/__init__.py — Registry of active news sources.

To add a new source: instantiate it here and append to SOURCES.
No other files need to change.
"""
import os

from data.sources.ars_technica import ArsTechnicaSource
from data.sources.base import NewsSource
from data.sources.reddit import RedditSource

SOURCES: list[NewsSource] = [
    RedditSource(subreddit=os.getenv("REDDIT_SUBREDDIT", "sysadmin")),
    ArsTechnicaSource(),
]
