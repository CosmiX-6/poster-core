"""Image sourcing cascade: real article images first, then stock, then AI."""

from __future__ import annotations

import httpx

from ..errors import ImageSourcingError
from ..models import Article, AssetPlan, ImageOrigin, SourcedImage
from .base import ImageGenerator, StockProvider

_TIMEOUT = 20.0


class ImageSourcer:
    """Resolves the best available image for a plan, following a policy.

    The default policy prefers the article's own photography, falls back to
    stock search, and only then generates an image with AI.
    """

    def __init__(
        self,
        policy: list[ImageOrigin] | None = None,
        stock: StockProvider | None = None,
        generator: ImageGenerator | None = None,
    ):
        self.policy = policy or [
            ImageOrigin.ARTICLE,
            ImageOrigin.STOCK,
            ImageOrigin.GENERATED,
        ]
        self.stock = stock
        self.generator = generator

    def source(
        self, plan: AssetPlan, article: Article, size: tuple[int, int]
    ) -> SourcedImage:
        for origin in self.policy:
            image = self._try_origin(origin, plan, article, size)
            if image is not None and image.data:
                return image
        raise ImageSourcingError(
            f"No image could be sourced for '{plan.headline}' with policy "
            f"{[o.value for o in self.policy]}"
        )

    def _try_origin(
        self,
        origin: ImageOrigin,
        plan: AssetPlan,
        article: Article,
        size: tuple[int, int],
    ) -> SourcedImage | None:
        if origin is ImageOrigin.ARTICLE and article.images:
            return self._fetch_article_image(article)
        if origin is ImageOrigin.STOCK and self.stock and plan.image_search_query:
            return self.stock.search(plan.image_search_query, size)
        if origin is ImageOrigin.GENERATED and self.generator:
            prompt = plan.image_generation_prompt or plan.headline
            data = self.generator.generate(prompt, size)
            return SourcedImage(
                origin=ImageOrigin.GENERATED, data=data, credit="AI-generated image"
            )
        return None

    @staticmethod
    def _fetch_article_image(article: Article) -> SourcedImage | None:
        for image in article.images:
            try:
                resp = httpx.get(image.url, timeout=_TIMEOUT, follow_redirects=True)
                resp.raise_for_status()
            except httpx.HTTPError:
                continue
            credit = f"Image: {article.source_name}" if article.source_name else None
            return SourcedImage(
                origin=ImageOrigin.ARTICLE,
                data=resp.content,
                credit=credit,
                source_url=image.url,
            )
        return None
