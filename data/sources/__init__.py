"""
data/sources/__init__.py — Registry of active news sources.

To add a new source: instantiate it here and append to SOURCES.
No other files need to change.
"""
import os

from data.sources.ars_technica import ArsTechnicaSource
from data.sources.base import NewsSource
from data.sources.reddit import RedditSource

_reddit = RedditSource(subreddit=os.getenv("REDDIT_SUBREDDIT", "sysadmin"))
_reddit.default_limit = int(os.getenv("REDDIT_LIMIT", "25"))

_ars = ArsTechnicaSource()
_ars.default_limit = int(os.getenv("ARS_LIMIT", "20"))

SOURCES: list[NewsSource] = [_reddit, _ars]
