"""Creative direction: turn a ContentBrief into concrete asset plans.

Planning is deterministic — the LLM already did the editorial work in the
brief — which keeps this step free, fast and unit-testable. Asset type
selection follows simple editorial heuristics when the caller doesn't
specify one.
"""

from __future__ import annotations

import re

from ..models import AssetPlan, AssetType, ContentBrief, Platform, StoryBeat

_NUMBERY = re.compile(r"\d")


def choose_asset_types(brief: ContentBrief) -> list[AssetType]:
    """Pick the most effective format(s) for this story."""
    types = [AssetType.COVER]
    if len(brief.story_beats) >= 3 or len(brief.timeline) >= 3:
        types.append(AssetType.CAROUSEL)
    numeric_facts = [f for f in brief.key_facts if _NUMBERY.search(f)]
    if len(numeric_facts) >= 3:
        types.append(AssetType.INFOGRAPHIC)
    return types


def plan_asset(
    brief: ContentBrief, asset_type: AssetType, platform: Platform
) -> AssetPlan:
    plan = AssetPlan(
        asset_type=asset_type,
        platform=platform,
        headline=brief.headline,
        subheadline=brief.subheadline,
        image_search_query=brief.image_search_query,
        image_generation_prompt=brief.image_generation_prompt,
    )
    if asset_type is AssetType.CAROUSEL:
        beats = brief.story_beats or [
            StoryBeat(heading=event.when, body=event.what) for event in brief.timeline
        ]
        plan.slides = beats or [StoryBeat(heading=brief.headline, body=brief.summary)]
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
