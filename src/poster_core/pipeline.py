"""End-to-end orchestration: ingest -> understand -> plan -> source -> render."""

from __future__ import annotations

import re
from pathlib import Path

from .analysis import plan_assets, understand
from .analysis.llm import GeminiChat, LLMClient, OpenAIChat
from .config import PipelineConfig
from .errors import ImageSourcingError
from .images import ChainedStockProvider, ImageSourcer
from .images.base import ImageGenerator, StockProvider
from .ingest import load
from .models import (
    Article,
    AssetPlan,
    AssetType,
    BrandKit,
    ContentBrief,
    GeneratedAsset,
    ImageOrigin,
    Platform,
    SourcedImage,
)
from .render import render_cover, render_deck, render_infographic


class Pipeline:
    """The main entry point for host projects.

    Every stage can be overridden by injecting your own `llm`, `generator`
    or `stock` implementation (see the protocols in `analysis.llm` and
    `images.base`), so the pipeline works with custom inputs and providers.
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        llm: LLMClient | None = None,
        generator: ImageGenerator | None = None,
        stock: StockProvider | None = None,
    ):
        self.config = config or PipelineConfig()
        self._llm = llm
        self._generator = generator
        self._stock = stock if stock is not None else ChainedStockProvider()

    # -- public API ---------------------------------------------------------

    def analyze(self, source: str | dict | Article) -> tuple[Article, ContentBrief]:
        """Run ingestion and editorial analysis without rendering anything."""
        article = load(source)
        return article, understand(article, self.llm)

    def run(
        self,
        source: str | dict | Article,
        asset_types: list[AssetType] | None = None,
        platform: Platform = Platform.INSTAGRAM_POST,
        output_dir: str | Path | None = None,
        size: tuple[int, int] | None = None,
        brand: BrandKit | None = None,
    ) -> list[GeneratedAsset]:
        """Produce publication-ready assets for one piece of content.

        When `asset_types` is None the creative-direction heuristics choose
        the most effective format(s) for the story. `size` overrides the
        platform's preset dimensions, and `brand` overrides the configured
        brand kit (channel name, footer, colours) for this run only.
        """
        article, brief = self.analyze(source)
        plans = plan_assets(brief, asset_types, platform)
        reading_minutes = max(1, round(len(article.text.split()) / 220))
        for plan in plans:
            if size is not None:
                plan.custom_size = size
            plan.source_name = article.source_name
            plan.reading_minutes = reading_minutes
        out = Path(output_dir or self.config.output_dir) / _slug(brief.headline)
        out.mkdir(parents=True, exist_ok=True)

        sourcer = ImageSourcer(
            policy=self.config.image_policy,
            stock=self._stock,
            generator=self.generator,
        )
        active_brand = brand or self.config.brand
        return [
            self._render_plan(plan, article, sourcer, out, active_brand)
            for plan in plans
        ]

    # -- internals ----------------------------------------------------------

    def _render_plan(
        self,
        plan: AssetPlan,
        article: Article,
        sourcer: ImageSourcer,
        out: Path,
        brand: BrandKit,
    ) -> GeneratedAsset:
        size = plan.size
        image: SourcedImage | None = None
        if plan.asset_type in (AssetType.COVER, AssetType.THUMBNAIL, AssetType.CAROUSEL):
            try:
                image = sourcer.source(plan, article, size)
            except ImageSourcingError:
                image = None  # heroes fall back to a typographic treatment

        paths: list[str] = []
        if plan.asset_type in (AssetType.COVER, AssetType.THUMBNAIL):
            img = render_cover(
                plan, image, brand, size,
                big_text=plan.asset_type is AssetType.THUMBNAIL,
            )
            paths.append(_save(img, out / f"{plan.asset_type.value}.png"))
        elif plan.asset_type is AssetType.CAROUSEL:
            for i, page in enumerate(render_deck(plan, image, brand), start=1):
                paths.append(_save(page, out / f"carousel_{i:02d}.png"))
        elif plan.asset_type is AssetType.INFOGRAPHIC:
            img = render_infographic(plan, brand, size)
            paths.append(_save(img, out / "infographic.png"))

        return GeneratedAsset(
            asset_type=plan.asset_type,
            platform=plan.platform,
            paths=paths,
            plan=plan,
            image_origin=image.origin if image else ImageOrigin.NONE,
            credit=image.credit if image else None,
        )

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            if self.config.text_provider == "gemini":
                self._llm = GeminiChat(model=self.config.gemini_text_model)
            else:
                self._llm = OpenAIChat(model=self.config.openai_text_model)
        return self._llm

    @property
    def generator(self) -> ImageGenerator | None:
        if self._generator is None and self.config.image_provider != "none":
            if self.config.image_provider == "gemini":
                from .images.gemini import GeminiImageGenerator

                self._generator = GeminiImageGenerator(
                    model=self.config.gemini_image_model
                )
            else:
                from .images.openai_images import OpenAIImageGenerator

                self._generator = OpenAIImageGenerator(
                    model=self.config.openai_image_model
                )
        return self._generator


def _slug(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len] or "asset"


def _save(img, path: Path) -> str:
    img.save(path, format="PNG")
    return str(path)
