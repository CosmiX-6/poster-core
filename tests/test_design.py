from poster_core.analysis.direct import build_deck
from poster_core.models import BrandKit, ContentBrief, SlideKind, StoryCategory
from poster_core.render import CATEGORY_THEMES, resolve_theme


def minimal_brief(**overrides) -> ContentBrief:
    data = dict(
        key_event="A thing happened.",
        summary="A thing happened somewhere to someone.",
        headline="A Thing Happened",
    )
    data.update(overrides)
    return ContentBrief.model_validate(data)


def test_every_category_has_a_theme():
    for category in StoryCategory:
        theme = CATEGORY_THEMES[category]
        assert theme.accent.startswith("#") and theme.background.startswith("#")


def test_semantic_colours_politics_red_finance_green():
    politics = resolve_theme(StoryCategory.POLITICS, BrandKit())
    finance = resolve_theme(StoryCategory.FINANCE, BrandKit())
    assert politics.accent == "#E0433D"
    assert finance.accent == "#34D399"


def test_custom_brand_accent_wins_over_category():
    brand = BrandKit(accent_color="#123456")
    theme = resolve_theme(StoryCategory.POLITICS, brand)
    assert theme.accent == "#123456"


def test_unknown_category_from_llm_coerces_to_general():
    brief = minimal_brief(category="celebrity gossip")
    assert brief.category is StoryCategory.GENERAL
    assert resolve_theme(brief.category, BrandKit()).label == "NEWS"


def test_deck_has_no_filler_for_thin_stories():
    brief = minimal_brief()
    slides = build_deck(brief)
    kinds = [s.kind for s in slides]
    # Nothing to build a timeline/stats/quote from: just hero + what happened.
    assert kinds == [SlideKind.HERO, SlideKind.TEXT]
    assert slides[1].kicker == "WHAT HAPPENED"


def test_deck_includes_only_supported_sections():
    brief = minimal_brief(
        key_facts=["£2m raised", "300 staff", "12 offices"],
        notable_quote={"text": "We grew fast", "attribution": "CEO"},
    )
    kinds = [s.kind for s in build_deck(brief)]
    assert SlideKind.STATS in kinds
    assert SlideKind.QUOTE in kinds
    assert SlideKind.TIMELINE not in kinds  # no timeline in the brief
