"""Pipeline configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .models import BrandKit, ImageOrigin


class PipelineConfig(BaseModel):
    """Configuration for a Pipeline.

    API keys are read from the standard environment variables of each
    provider (OPENAI_API_KEY, GOOGLE_API_KEY, UNSPLASH_ACCESS_KEY,
    PEXELS_API_KEY) unless a provider instance is injected directly.
    """

    text_provider: Literal["openai", "gemini"] = "openai"
    openai_text_model: str = "gpt-4o-mini"
    gemini_text_model: str = "gemini-flash-latest"

    image_provider: Literal["openai", "gemini", "none"] = "openai"
    openai_image_model: str = "gpt-image-1"
    gemini_image_model: str = "imagen-4.0-fast-generate-001"

    image_policy: list[ImageOrigin] = Field(
        default_factory=lambda: [
            ImageOrigin.ARTICLE,
            ImageOrigin.STOCK,
            ImageOrigin.GENERATED,
        ]
    )
    output_dir: str = "output"
    brand: BrandKit = Field(default_factory=BrandKit)
