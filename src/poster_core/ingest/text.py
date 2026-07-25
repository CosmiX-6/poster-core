"""Raw-text ingestion."""

from __future__ import annotations

from ..models import Article


def article_from_text(text: str, title: str | None = None) -> Article:
    """Build an Article from raw text; first line is the title if not given."""
    stripped = text.strip()
    if title is None:
        first, _, rest = stripped.partition("\n")
        title = first.strip()
        body = rest.strip() or first.strip()
    else:
        body = stripped
    return Article(title=title, text=body)
