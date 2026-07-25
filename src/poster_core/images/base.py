"""Provider protocols for image generation and stock search."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import SourcedImage


@runtime_checkable
class ImageGenerator(Protocol):
    def generate(self, prompt: str, size: tuple[int, int]) -> bytes: ...


@runtime_checkable
class StockProvider(Protocol):
    def search(self, query: str, size: tuple[int, int]) -> SourcedImage | None: ...


def orientation_for(size: tuple[int, int]) -> str:
    w, h = size
    if w > h * 1.1:
        return "landscape"
    if h > w * 1.1:
        return "portrait"
    return "squarish"
