from pathlib import Path

import pytest
from PIL import Image

from poster_core import Pipeline, PipelineConfig
from poster_core.errors import ImageSourcingError
from poster_core.images.sourcing import ImageSourcer
from poster_core.models import (
    Article,
    AssetType,
    ImageOrigin,
    Platform,
    PLATFORM_SIZES,
)

ARTICLE_TEXT = "Acme Launch\nAcme Corp launched its first reusable rocket on Tuesday."


def make_pipeline(tmp_path, fake_llm, fake_generator, fake_stock) -> Pipeline:
    config = PipelineConfig(output_dir=str(tmp_path))
    return Pipeline(config, llm=fake_llm, generator=fake_generator, stock=fake_stock)


def test_full_run_produces_expected_assets(tmp_path, fake_llm, fake_generator, fake_stock):
    pipe = make_pipeline(tmp_path, fake_llm, fake_generator, fake_stock)
    assets = pipe.run(ARTICLE_TEXT)  # auto asset selection

    types = {a.asset_type for a in assets}
    assert types == {AssetType.COVER, AssetType.CAROUSEL, AssetType.INFOGRAPHIC}
    for asset in assets:
        for path in asset.paths:
            assert Path(path).exists()
            with Image.open(path) as img:
                assert img.size == PLATFORM_SIZES[Platform.INSTAGRAM_POST]

    cover = next(a for a in assets if a.asset_type is AssetType.COVER)
    assert cover.image_origin is ImageOrigin.STOCK  # no article image -> stock hit
    assert cover.credit == "Photo: Test / Unsplash"

    carousel = next(a for a in assets if a.asset_type is AssetType.CAROUSEL)
    assert len(carousel.paths) == 4  # image slide + 3 beats


def test_generation_fallback_when_stock_misses(tmp_path, fake_llm, fake_generator, fake_stock):
    fake_stock.hit = False
    pipe = make_pipeline(tmp_path, fake_llm, fake_generator, fake_stock)
    assets = pipe.run(ARTICLE_TEXT, asset_types=[AssetType.COVER])
    assert assets[0].image_origin is ImageOrigin.GENERATED
    assert fake_generator.prompts  # generation prompt was used


def test_cover_fails_without_any_image_source(tmp_path, fake_llm, fake_stock):
    fake_stock.hit = False
    config = PipelineConfig(output_dir=str(tmp_path), image_provider="none")
    pipe = Pipeline(config, llm=fake_llm, stock=fake_stock)
    with pytest.raises(ImageSourcingError):
        pipe.run(ARTICLE_TEXT, asset_types=[AssetType.COVER])


def test_carousel_renders_without_images(tmp_path, fake_llm, fake_stock):
    fake_stock.hit = False
    config = PipelineConfig(output_dir=str(tmp_path), image_provider="none")
    pipe = Pipeline(config, llm=fake_llm, stock=fake_stock)
    assets = pipe.run(ARTICLE_TEXT, asset_types=[AssetType.CAROUSEL])
    assert len(assets[0].paths) == 3  # typographic slides only
    assert assets[0].image_origin is ImageOrigin.NONE


def test_platform_sizes_respected(tmp_path, fake_llm, fake_generator, fake_stock):
    pipe = make_pipeline(tmp_path, fake_llm, fake_generator, fake_stock)
    assets = pipe.run(
        ARTICLE_TEXT,
        asset_types=[AssetType.THUMBNAIL],
        platform=Platform.YOUTUBE_THUMBNAIL,
    )
    with Image.open(assets[0].paths[0]) as img:
        assert img.size == (1280, 720)


def test_sourcer_prefers_article_image(monkeypatch, fake_stock):
    from poster_core.models import ArticleImage, AssetPlan, SourcedImage
    from conftest import solid_png

    article = Article(
        title="t", text="x", source_name="Example News",
        images=[ArticleImage(url="https://example.com/hero.jpg")],
    )

    def fake_fetch(article):
        return SourcedImage(
            origin=ImageOrigin.ARTICLE, data=solid_png(), credit="Image: Example News"
        )

    sourcer = ImageSourcer(stock=fake_stock)
    monkeypatch.setattr(ImageSourcer, "_fetch_article_image", staticmethod(fake_fetch))
    plan = AssetPlan(
        asset_type=AssetType.COVER, platform=Platform.X,
        headline="h", image_search_query="q",
    )
    result = sourcer.source(plan, article, (1600, 900))
    assert result.origin is ImageOrigin.ARTICLE
    assert fake_stock.queries == []  # never reached stock
