"""Article understanding: one LLM call turning an Article into a ContentBrief."""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..errors import AnalysisError
from ..models import Article, ContentBrief
from .llm import LLMClient

_SYSTEM = """\
You are a senior news editor and creative director. You analyse articles and
produce a structured editorial brief used to design social media visuals.
Be factually faithful to the article; never invent facts, names or numbers.
Respond with a single JSON object only."""

_INSTRUCTIONS = """\
Analyse the article above and return JSON with exactly these keys:
- key_event: one sentence, the single most newsworthy thing that happened
- summary: 2-3 sentence neutral summary
- headline: punchy, accurate headline for a social visual, max 9 words
- subheadline: one supporting line, max 16 words (or null)
- entities: list of {"name": str, "kind": "person"|"organisation"|"place"|"product"|"other"}
- key_facts: 3-6 short, self-contained facts or stats worth showing on a graphic
- timeline: chronological list of {"when": str, "what": str} (empty if not applicable)
- story_beats: 3-6 {"heading": str, "body": str} steps that explain the story in
  sequence, each heading max 7 words, each body max 30 words
- emotions: 1-3 dominant emotions the story evokes
- tone: one of "urgent", "celebratory", "sombre", "analytical", "neutral", "inspiring"
- visual_concepts: 2-3 distinct ideas for a hero image, described concretely
- image_search_query: 2-5 word stock-photo search query for the best concept
- image_generation_prompt: detailed, photorealistic-by-default prompt for an AI
  image model depicting the best concept; no text in the image, no real people's
  faces, no logos"""


def understand(article: Article, llm: LLMClient, max_chars: int = 12000) -> ContentBrief:
    body = article.text[:max_chars]
    user = (
        f"TITLE: {article.title}\n"
        + (f"SOURCE: {article.source_name}\n" if article.source_name else "")
        + (f"PUBLISHED: {article.published_at}\n" if article.published_at else "")
        + f"\nARTICLE:\n{body}\n\n{_INSTRUCTIONS}"
    )
    data = llm.complete_json(_SYSTEM, user)
    try:
        return ContentBrief.model_validate(data)
    except ValidationError as exc:
        raise AnalysisError(
            f"LLM brief failed validation: {exc}\nraw: {json.dumps(data)[:500]}"
        ) from exc
