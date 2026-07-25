"""RSS/Atom ingestion for newsroom feeds and press portals."""

from __future__ import annotations

import feedparser

from ..errors import IngestError
from ..models import Article
from .url import load_url


def load_feed(feed_url: str, limit: int = 10, fetch_full: bool = True) -> list[Article]:
    """Load up to `limit` entries from an RSS/Atom feed.

    When `fetch_full` is true, each entry's link is fetched and fully
    extracted; entries whose pages can't be fetched fall back to the feed's
    own summary text.
    """
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        raise IngestError(f"Could not parse feed {feed_url}: {parsed.bozo_exception}")

    articles: list[Article] = []
    for entry in parsed.entries[:limit]:
        articles.append(article_from_entry(entry, fetch_full=fetch_full))
    return articles


def article_from_entry(entry, fetch_full: bool = True) -> Article:
    link = entry.get("link")
    if fetch_full and link:
        try:
            return load_url(link)
        except IngestError:
            pass  # fall back to feed-provided content

    summary = entry.get("summary", "") or ""
    content = entry.get("content")
    if content:
        summary = content[0].get("value", summary)
    from bs4 import BeautifulSoup

    text = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
    if not text:
        raise IngestError(f"Feed entry has no usable content: {link or entry.get('title')}")
    return Article(title=entry.get("title", text[:120]), text=text, url=link)
