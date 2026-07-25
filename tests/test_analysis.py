from poster_core.analysis import choose_asset_types, plan_assets, understand
from poster_core.analysis.llm import parse_json_response
from poster_core.errors import AnalysisError
from poster_core.models import Article, AssetType, Platform

import pytest


def test_understand_returns_valid_brief(fake_llm):
    article = Article(title="Rocket launch", text="Acme launched a rocket.")
    brief = understand(article, fake_llm)
    assert brief.headline
    assert len(brief.story_beats) == 3
    assert "Rocket launch" in fake_llm.calls[0][1]


def test_parse_json_tolerates_code_fences():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_response('noise {"a": {"b": 2}} trailing') == {"a": {"b": 2}}
    with pytest.raises(AnalysisError):
        parse_json_response("no json here")


def test_choose_asset_types_prefers_carousel_and_infographic(fake_llm):
    article = Article(title="t", text="x")
    brief = understand(article, fake_llm)
    types = choose_asset_types(brief)
    assert types[0] is AssetType.COVER
    assert AssetType.CAROUSEL in types
    assert AssetType.INFOGRAPHIC in types  # three numeric facts


def test_plan_assets_carousel_falls_back_to_timeline(fake_llm):
    fake_llm.overrides = {"story_beats": []}
    article = Article(title="t", text="x")
    brief = understand(article, fake_llm)
    plans = plan_assets(brief, [AssetType.CAROUSEL], Platform.INSTAGRAM_POST)
    assert len(plans[0].slides) == 3  # from timeline
    assert plans[0].slides[0].heading == "Tuesday 09:00"


def test_thumbnail_headline_is_shortened(fake_llm):
    article = Article(title="t", text="x")
    brief = understand(article, fake_llm)
    plans = plan_assets(brief, [AssetType.THUMBNAIL], Platform.YOUTUBE_THUMBNAIL)
    assert len(plans[0].headline.split()) <= 5
    assert plans[0].subheadline is None
