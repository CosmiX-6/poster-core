"""Stock photo providers: Unsplash and Pexels."""

from __future__ import annotations

import os

import httpx

from ..models import ImageOrigin, SourcedImage
from .base import orientation_for

_TIMEOUT = 20.0


class UnsplashProvider:
    """Requires UNSPLASH_ACCESS_KEY (or an explicit access_key)."""

    def __init__(self, access_key: str | None = None):
        self.access_key = access_key or os.environ.get("UNSPLASH_ACCESS_KEY")

    @property
    def available(self) -> bool:
        return bool(self.access_key)

    def search(self, query: str, size: tuple[int, int]) -> SourcedImage | None:
        if not self.available:
            return None
        resp = httpx.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query,
                "per_page": 1,
                "orientation": orientation_for(size),
                "content_filter": "high",
            },
            headers={"Authorization": f"Client-ID {self.access_key}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        photo = results[0]
        data = httpx.get(photo["urls"]["regular"], timeout=_TIMEOUT).content
        photographer = photo.get("user", {}).get("name", "Unknown")
        return SourcedImage(
            origin=ImageOrigin.STOCK,
            data=data,
            credit=f"Photo: {photographer} / Unsplash",
            source_url=photo.get("links", {}).get("html"),
        )


class PexelsProvider:
    """Requires PEXELS_API_KEY (or an explicit api_key)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, size: tuple[int, int]) -> SourcedImage | None:
        if not self.available:
            return None
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": query,
                "per_page": 1,
                "orientation": orientation_for(size).replace("squarish", "square"),
            },
            headers={"Authorization": self.api_key},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = photos[0]
        data = httpx.get(photo["src"]["large2x"], timeout=_TIMEOUT).content
        return SourcedImage(
            origin=ImageOrigin.STOCK,
            data=data,
            credit=f"Photo: {photo.get('photographer', 'Unknown')} / Pexels",
            source_url=photo.get("url"),
        )


class ChainedStockProvider:
    """Tries each configured provider in order, skipping unavailable ones."""

    def __init__(self, providers: list | None = None):
        self.providers = providers if providers is not None else [
            UnsplashProvider(),
            PexelsProvider(),
        ]

    def search(self, query: str, size: tuple[int, int]) -> SourcedImage | None:
        for provider in self.providers:
            if getattr(provider, "available", True):
                try:
                    result = provider.search(query, size)
                except httpx.HTTPError:
                    continue
                if result is not None:
                    return result
        return None
