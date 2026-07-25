"""Creative direction: turn a ContentBrief into concrete asset plans.

Planning is deterministic — the LLM already did the editorial work in the
brief — which keeps this step free, fast and unit-testable. Carousels are
composed as a narrative deck (hero, story, timeline, numbers, quote,
why-it-matters, what's-next) and only include slides the story actually
supports; no filler.
"""

from __future__ import annotations

import re

from ..models import (
    AssetPlan,
    AssetType,
    ContentBrief,
    DeckSlide,
    Platform,
    SlideKind,
)

_NUMBERY = re.compile(r"\d")

MAX_DECK_SLIDES = 8


def choose_asset_types(brief: ContentBrief) -> list[AssetType]:
    """Pick the most effective format(s) for this story."""
    types = [AssetType.COVER]
    if len(brief.story_beats) >= 3 or len(brief.timeline) >= 3:
        types.append(AssetType.CAROUSEL)
    if len(numeric_facts(brief)) >= 3:
        types.append(AssetType.INFOGRAPHIC)
    return types


def numeric_facts(brief: ContentBrief) -> list[str]:
    return [f for f in brief.key_facts if _NUMBERY.search(f)]


def build_deck(brief: ContentBrief) -> list[DeckSlide]:
    """Compose a carousel narrative from whatever the story supports."""
    slides = [
        DeckSlide(
            kind=SlideKind.HERO, heading=brief.headline, body=brief.subheadline
        )
    ]
    if brief.story_beats:
        slides += [
            DeckSlide(kind=SlideKind.TEXT, heading=b.heading, body=b.body)
            for b in brief.story_beats[:4]
        ]
    else:
        slides.append(
            DeckSlide(
                kind=SlideKind.TEXT,
                kicker="WHAT HAPPENED",
                heading=brief.key_event,
                body=brief.summary,
            )
        )
    if len(brief.timeline) >= 3:
        slides.append(
            DeckSlide(
                kind=SlideKind.TIMELINE,
                kicker="HOW IT UNFOLDED",
                timeline=brief.timeline[:5],
            )
        )
    numbers = numeric_facts(brief)
    if len(numbers) >= 2:
        slides.append(
            DeckSlide(kind=SlideKind.STATS, kicker="KEY NUMBERS", facts=numbers[:4])
        )
    if brief.notable_quote:
        slides.append(DeckSlide(kind=SlideKind.QUOTE, quote=brief.notable_quote))
    if brief.why_it_matters:
        slides.append(
            DeckSlide(
                kind=SlideKind.TEXT, kicker="WHY IT MATTERS", body=brief.why_it_matters
            )
        )
    if brief.future_impact:
        slides.append(
            DeckSlide(
                kind=SlideKind.TEXT, kicker="WHAT'S NEXT", body=brief.future_impact
            )
        )
    return slides[:MAX_DECK_SLIDES]


def plan_asset(
    brief: ContentBrief, asset_type: AssetType, platform: Platform
) -> AssetPlan:
    plan = AssetPlan(
        asset_type=asset_type,
        platform=platform,
        headline=brief.headline,
        subheadline=brief.subheadline,
        category=brief.category,
        image_search_query=brief.image_search_query,
        image_generation_prompt=brief.image_generation_prompt,
    )
    if asset_type is AssetType.CAROUSEL:
        plan.slides = build_deck(brief)
    elif asset_type is AssetType.INFOGRAPHIC:
        plan.facts = brief.key_facts or [brief.key_event]
    elif asset_type is AssetType.THUMBNAIL:
        # Thumbnails need short, high-impact text.
        plan.headline = _shorten(brief.headline, max_words=5)
        plan.subheadline = None
    return plan


def plan_assets(
    brief: ContentBrief,
    asset_types: list[AssetType] | None,
    platform: Platform,
) -> list[AssetPlan]:
    types = asset_types or choose_asset_types(brief)
    return [plan_asset(brief, t, platform) for t in types]


def _shorten(text: str, max_words: int) -> str:
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])
