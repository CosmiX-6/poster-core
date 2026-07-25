"""OpenAI image generation provider (requires the `openai` extra)."""

from __future__ import annotations

import base64
import os


class OpenAIImageGenerator:
    def __init__(self, model: str = "gpt-image-1", api_key: str | None = None):
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def generate(self, prompt: str, size: tuple[int, int]) -> bytes:
        result = self._client.images.generate(
            model=self.model, prompt=prompt, size=self._nearest_size(size), n=1
        )
        return base64.b64decode(result.data[0].b64_json)

    @staticmethod
    def _nearest_size(size: tuple[int, int]) -> str:
        w, h = size
        if w > h * 1.1:
            return "1536x1024"
        if h > w * 1.1:
            return "1024x1536"
        return "1024x1024"
