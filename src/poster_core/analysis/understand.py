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
- headline: an editorial headline written for a social visual (do NOT copy the
  article title), clear and engaging, 8-12 words max
- subheadline: one supporting line, max 16 words (or null)
- hook: a short, curiosity-first opening line for slide one of a swipeable
  carousel — NOT the headline, and never a plain restatement of it. It should
  make someone want to keep swiping without giving away the ending. Lead with
  a striking number, tension, or an open question, grounded only in facts
  actually in the article. Examples of the STYLE (write your own, don't copy):
  "£500,000. One company. One investigation." / "The paper trail nobody
  expected." / "It started with a single wire transfer." 6-14 words.
- category: exactly one of "breaking", "investigation", "politics",
  "technology", "ai", "finance", "business", "sports", "science", "health",
  "disaster", "product_launch", "general" — pick what best drives the visual
  treatment of this story
- notable_quote: {"text": str, "attribution": str} — the single most striking
  short quote actually present in the article, or null if none stands out
- why_it_matters: 1-2 sentences on why this story matters to the reader
  (or null)
- future_impact: one sentence on what happens next, only if the article
  supports it (or null)
- closing_line: one memorable closing line for the FINAL slide of the
  carousel — a forward-looking statement, an open question, or a striking
  restatement of the stakes. Must be grounded in the article, never
  speculative beyond what it supports (e.g. "The investigation is still
  ongoing." or "The next hearing is expected within weeks."). Null if the
  article gives nothing to close on.
- entities: list of {"name": str, "kind": "person"|"organisation"|"place"|"product"|"other"}
- key_facts: 3-6 short, self-contained facts or stats worth showing on a graphic
- timeline: chronological list of {"when": str, "what": str} (empty if not applicable)
- story_beats: 3-6 {"heading": str, "body": str} steps that explain the story in
  sequence, each heading max 7 words, each body max 30 words
- money_trail: ONLY if the article describes money moving between specific
  people/organisations (donations, transfers, funding, payments) — a
  chronological list of 2-4 {"actor": str, "amount": str|null, "detail":
  str|null} steps, where each step's "amount" is the sum that arrived at
  that actor from the previous step (the first step's amount is null, since
  nothing arrives there — it's the origin). Empty list if no clear money
  trail exists; do not force one.
- comparison: ONLY if the article supports a clear two-way comparison
  (before/after, this year vs last, X vs Y) — {"title": str|null, "label_a":
  str, "value_a": str, "label_b": str, "value_b": str}. Null if nothing
  compares cleanly.
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
