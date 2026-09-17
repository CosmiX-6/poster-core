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
    # Nothing to build a timeline/stats/quote/money-trail from: just the
    # cold open, what happened, and the closing CTA (always present).
    assert kinds == [SlideKind.HOOK, SlideKind.TEXT, SlideKind.CTA]
    assert slides[1].kicker == "WHAT HAPPENED"
    assert slides[0].heading == brief.headline  # falls back when no hook given
    assert slides[0].transition is not None
    assert slides[1].transition is not None
    assert slides[2].transition is None  # last slide never baits a swipe


def test_deck_includes_only_supported_sections():
    brief = minimal_brief(
        key_facts=["£2m raised", "300 staff", "12 offices"],
        notable_quote={"text": "We grew fast", "attribution": "CEO"},
    )
    kinds = [s.kind for s in build_deck(brief)]
    assert SlideKind.STATS in kinds
    assert SlideKind.QUOTE in kinds
    assert SlideKind.TIMELINE not in kinds  # no timeline in the brief
    assert SlideKind.MONEY_FLOW not in kinds  # no money trail in the brief
    assert SlideKind.COMPARISON not in kinds  # no comparison in the brief


def test_deck_never_repeats_consecutive_layouts():
    # Two story beats plus why-it-matters: three text-driven sections in a
    # row is exactly the case that used to render as three identical slides.
    brief = minimal_brief(
        story_beats=[
            {"heading": "First beat", "body": "Body one."},
            {"heading": "Second beat", "body": "Body two."},
        ],
        why_it_matters="This matters because of reasons.",
    )
    kinds = [s.kind for s in build_deck(brief)]
    for a, b in zip(kinds, kinds[1:]):
        assert a != b


def test_money_trail_requires_at_least_two_steps():
    brief = minimal_brief(money_trail=[{"actor": "Solo actor"}])
    kinds = [s.kind for s in build_deck(brief)]
    assert SlideKind.MONEY_FLOW not in kinds
