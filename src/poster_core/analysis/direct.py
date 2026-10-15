"""Creative direction: turn a ContentBrief into concrete asset plans.

Planning is deterministic — the LLM already did the editorial work in the
brief — which keeps this step free, fast and unit-testable. Carousels are
composed as a documentary-style deck: a cold-open hook, then chapters that
each introduce one new piece of information, ending on a deliberate close.
Only sections the story actually supports are included — no filler — and
consecutive slides are guaranteed to never share the same layout, so the
swipe never feels repetitive.
"""

from __future__ import annotations

import re

from ..models import (
    AssetPlan,
    AssetType,
    BrandKit,
    ContentBrief,
    DeckSlide,
    Platform,
    SlideKind,
    StoryBeat,
    StoryCategory,
)

_NUMBERY = re.compile(r"\d")

# Instagram/Threads carousels cap at 10 images; our documentary structure
# (hook + up to 2 beats + why-it-matters + money trail + timeline + stats +
# comparison + quote + conclusion) tops out at exactly 10, so this is a
# defensive ceiling rather than something that normally truncates content.
MAX_DECK_SLIDES = 10

# Generic, non-factual transition lines shown at the bottom of a slide to
# bait the next swipe. They never assert anything about the story itself,
# so they carry no risk of contradicting the article.
_TRANSITIONS = [
    "But that wasn't where the story began.",
    "Then investigators found something else.",
    "Here's where it gets complicated.",
    "That number alone doesn't tell the story.",
    "But the timeline raises new questions.",
    "Here's where the money actually went.",
    "Now comes the key question.",
    "That isn't the biggest number.",
    "But one detail changes everything.",
]


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


def _append_text_like(
    slides: list[DeckSlide], kicker: str, heading: str | None, body: str | None
) -> None:
    """Append a text-driven slide, alternating between the plain TEXT layout
    and the framed EVIDENCE layout so two prose slides never sit back to
    back with an identical look."""
    kind = SlideKind.EVIDENCE if slides and slides[-1].kind is SlideKind.TEXT else SlideKind.TEXT
    slides.append(DeckSlide(kind=kind, kicker=kicker, heading=heading, body=body))


def build_deck(brief: ContentBrief, brand: BrandKit | None = None) -> list[DeckSlide]:
    """Narrative-arc carousel: hook → what → why → impact → data → bigger
    picture → conclusion → CTA. Each slide introduces exactly one idea; the
    story decodes the *problem behind the news*, not just the event itself.
    Only sections the brief actually supports are included; no filler."""
    slides: list[DeckSlide] = [
        DeckSlide(kind=SlideKind.HOOK, heading=brief.hook or brief.headline)
    ]

    # WHAT — the event itself
    beats = brief.story_beats or [StoryBeat(heading=brief.key_event, body=brief.summary)]
    first = beats[0]
    _append_text_like(slides, "WHAT HAPPENED", first.heading, first.body or brief.summary)

    # WHY — root cause (one sentence, displayed as a big headline)
    if brief.root_cause:
        slides.append(
            DeckSlide(kind=SlideKind.WHY, kicker="WHY IT'S HAPPENING", heading=brief.root_cause)
        )
    elif len(beats) > 1:
        second = beats[1]
        _append_text_like(slides, "THE DETAIL", second.heading, second.body)

    # IMPACT — who gains, who pays; lead line as heading, details as body
    if brief.who_benefits or brief.who_is_hurt:
        impact_head, impact_body = _build_impact_slide(brief)
        slides.append(
            DeckSlide(
                kind=SlideKind.IMPACT, kicker="WHO WINS / WHO LOSES",
                heading=impact_head, body=impact_body,
            )
        )

    # Data scenes — only what the story actually supports
    if len(brief.money_trail) >= 2:
        slides.append(
            DeckSlide(
                kind=SlideKind.MONEY_FLOW,
                kicker="FOLLOW THE MONEY",
                money_trail=brief.money_trail[:4],
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
        # Surface the single most striking number as a SCREAM scene when the
        # story is data-heavy (AI, finance, science) and there are enough
        # numbers to also fill a STATS scene.
        if len(numbers) >= 3 and brief.category in _SCREAM_CATEGORIES:
            slides.append(
                DeckSlide(kind=SlideKind.SCREAM, kicker="THE NUMBER", facts=[numbers[0]])
            )
            slides.append(
                DeckSlide(kind=SlideKind.STATS, kicker="BY THE NUMBERS", facts=numbers[1:4])
            )
        else:
            slides.append(
                DeckSlide(kind=SlideKind.STATS, kicker="BY THE NUMBERS", facts=numbers[:4])
            )

    if brief.comparison:
        slides.append(
            DeckSlide(
                kind=SlideKind.COMPARISON,
                kicker=brief.comparison.title or "BEFORE / AFTER",
                comparison=brief.comparison,
            )
        )

    if brief.notable_quote:
        slides.append(DeckSlide(kind=SlideKind.QUOTE, quote=brief.notable_quote))

    # BIGGER PICTURE — one sentence as a big headline
    if brief.bigger_picture:
        slides.append(
            DeckSlide(
                kind=SlideKind.BIGGER_PICTURE,
                kicker="THE BIGGER PICTURE",
                heading=brief.bigger_picture,
            )
        )

    # CONCLUSION — what comes next
    closing = brief.closing_line or brief.future_impact
    if closing:
        slides.append(
            DeckSlide(kind=SlideKind.CONCLUSION, kicker="WHAT HAPPENS NEXT", body=closing)
        )

    # Reserve the last slot for the CTA — every deck ends by asking for the follow.
    slides = slides[: MAX_DECK_SLIDES - 1]
    slides.append(_build_cta_slide(brief, brand or BrandKit()))
    _assign_transitions(slides)
    return slides


# Categories where a single oversized stat is worth its own SCREAM scene.
_SCREAM_CATEGORIES = {
    StoryCategory.AI, StoryCategory.TECHNOLOGY, StoryCategory.FINANCE,
    StoryCategory.SCIENCE, StoryCategory.HEALTH, StoryCategory.BUSINESS,
}


def _build_impact_slide(brief: ContentBrief) -> tuple[str | None, str | None]:
    """Heading = the primary winner or loser; body = remaining details."""
    head = brief.who_benefits or brief.who_is_hurt
    parts = []
    if brief.who_benefits and brief.who_is_hurt:
        parts.append(f"Loses: {brief.who_is_hurt}")
    if brief.real_cost:
        parts.append(f"Cost: {brief.real_cost}")
    body = "  \n".join(parts) if parts else None
    return head, body


def _build_cta_slide(brief: ContentBrief, brand: BrandKit) -> DeckSlide:
    heading = (
        f"Follow @{brand.social_handle} for daily breakdowns"
        if brand.social_handle
        else "Follow for daily breakdowns"
    )
    # Use the bigger_picture or closing_line as a story-specific payoff body
    # so the CTA ties back to the narrative rather than being generic.
    payoff = brief.bigger_picture or brief.closing_line or brief.future_impact
    body = _shorten(payoff, max_words=12) if payoff else _shorten(brief.headline, max_words=10)
    return DeckSlide(kind=SlideKind.CTA, heading=heading, body=body)


def _assign_transitions(slides: list[DeckSlide]) -> None:
    """Give every slide but the last a swipe-bait line for the next one."""
    for i, slide in enumerate(slides[:-1]):
        slide.transition = _TRANSITIONS[i % len(_TRANSITIONS)]


def plan_asset(
    brief: ContentBrief, asset_type: AssetType, platform: Platform,
    brand: BrandKit | None = None,
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
        plan.slides = build_deck(brief, brand)
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
    brand: BrandKit | None = None,
) -> list[AssetPlan]:
    types = asset_types or choose_asset_types(brief)
    return [plan_asset(brief, t, platform, brand) for t in types]


def _shorten(text: str, max_words: int) -> str:
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])
