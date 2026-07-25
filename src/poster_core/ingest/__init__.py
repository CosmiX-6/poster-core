"""Content ingestion: normalise any supported input into an Article."""

from __future__ import annotations

from ..errors import IngestError
from ..models import Article
from .rss import load_feed
from .text import article_from_text
from .url import load_url

__all__ = ["load", "load_url", "load_feed", "article_from_text"]


def load(source: "str | dict | Article") -> Article:
    """Normalise a source into an Article.

    Accepts an Article (passthrough), a dict of Article fields, an http(s)
    URL, or raw text (first line becomes the title).
    """
    if isinstance(source, Article):
        return source
    if isinstance(source, dict):
        return Article.model_validate(source)
    if isinstance(source, str):
        stripped = source.strip()
        if not stripped:
            raise IngestError("Empty source")
        if stripped.startswith(("http://", "https://")):
            return load_url(stripped)
        return article_from_text(stripped)
    raise IngestError(f"Unsupported source type: {type(source).__name__}")
