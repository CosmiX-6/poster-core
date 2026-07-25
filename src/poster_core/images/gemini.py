"""Google Imagen generation provider (requires the `gemini` extra)."""

from __future__ import annotations

import os


class GeminiImageGenerator:
    def __init__(
        self, model: str = "imagen-4.0-fast-generate-001", api_key: str | None = None
    ):
        from google import genai

        self.model = model
        self._client = genai.Client(api_key=api_key or os.environ.get("GOOGLE_API_KEY"))

    def generate(self, prompt: str, size: tuple[int, int]) -> bytes:
        from google.genai import types

        resp = self._client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1, aspect_ratio=self._nearest_aspect(size)
            ),
        )
        return resp.generated_images[0].image.image_bytes

    @staticmethod
    def _nearest_aspect(size: tuple[int, int]) -> str:
        w, h = size
        ratio = w / h
        aspects = {"1:1": 1.0, "4:3": 4 / 3, "3:4": 3 / 4, "16:9": 16 / 9, "9:16": 9 / 16}
        return min(aspects, key=lambda a: abs(aspects[a] - ratio))
