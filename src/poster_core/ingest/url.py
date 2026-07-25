"""URL ingestion: fetch a page and extract title, body text and images."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ..errors import IngestError
from ..models import Article, ArticleImage

_UA = "Mozilla/5.0 (compatible; poster-core/0.1; +https://example.invalid)"


def load_url(url: str, timeout: float = 20.0) -> Article:
    try:
        resp = httpx.get(
            url, timeout=timeout, follow_redirects=True, headers={"User-Agent": _UA}
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise IngestError(f"Failed to fetch {url}: {exc}") from exc
    return article_from_html(resp.text, url=url)


def article_from_html(html: str, url: str | None = None) -> Article:
    text = _extract_with_trafilatura(html)
    soup = BeautifulSoup(html, "html.parser")

    title = _meta(soup, "og:title") or (soup.title.get_text(strip=True) if soup.title else "")
    if text is None:
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = "\n\n".join(p for p in paragraphs if len(p) > 40)
    if not text.strip():
        raise IngestError(f"Could not extract article text from {url or 'HTML'}")

    images: list[ArticleImage] = []
    og_image = _meta(soup, "og:image")
    if og_image and url:
        og_image = urljoin(url, og_image)
    if og_image:
        images.append(ArticleImage(url=og_image))

    site_name = _meta(soup, "og:site_name")
    return Article(
        title=title or text.split("\n", 1)[0][:120],
        text=text.strip(),
        url=url,
        source_name=site_name,
        images=images,
    )


def _meta(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop}) or soup.find(
        "meta", attrs={"name": prop}
    )
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _extract_with_trafilatura(html: str) -> str | None:
    try:
        import trafilatura
    except ImportError:
        return None
    return trafilatura.extract(html)
