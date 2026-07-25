import io

import pytest
from PIL import Image

from poster_core.models import ImageOrigin, SourcedImage


class FakeLLM:
    """Returns a canned editorial brief; records the prompts it was given."""

    def __init__(self, overrides: dict | None = None):
        self.calls: list[tuple[str, str]] = []
        self.overrides = overrides or {}

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        brief = {
            "key_event": "Acme Corp launched a reusable rocket.",
            "summary": "Acme Corp launched its first reusable rocket on Tuesday. "
            "The booster landed successfully after delivering 20 satellites.",
            "headline": "Acme's First Reusable Rocket Sticks the Landing",
            "subheadline": "20 satellites delivered before a flawless booster return",
            "hook": "One booster. Twenty satellites. Zero margin for error.",
            "entities": [{"name": "Acme Corp", "kind": "organisation"}],
            "key_facts": [
                "20 satellites deployed in one launch",
                "Booster landed 8 minutes after liftoff",
                "Launch costs cut by an estimated 60%",
            ],
            "timeline": [
                {"when": "Tuesday 09:00", "what": "Liftoff from pad 4"},
                {"when": "09:05", "what": "Satellites deployed"},
                {"when": "09:08", "what": "Booster landing"},
            ],
            "story_beats": [
                {"heading": "The launch", "body": "Acme's rocket lifted off Tuesday."},
                {"heading": "The payload", "body": "20 satellites reached orbit."},
                {"heading": "The landing", "body": "The booster returned intact."},
            ],
            "category": "science",
            "notable_quote": {
                "text": "This changes the economics of space entirely",
                "attribution": "Dana Reeve, Acme chief engineer",
            },
            "why_it_matters": "Reusable boosters slash the cost of reaching "
            "orbit, opening space to far more operators.",
            "future_impact": "Acme plans a second flight within six weeks.",
            "closing_line": "Acme says a second launch is already being scheduled.",
            "money_trail": [
                {"actor": "Orbital Ventures (investor)", "amount": None, "detail": None},
                {"actor": "Acme Holdings", "amount": "$120,000,000", "detail": "Series C, 2023"},
                {"actor": "Acme Corp R&D", "amount": "$45,000,000", "detail": "Booster program"},
            ],
            "comparison": {
                "title": "COST PER LAUNCH",
                "label_a": "BEFORE REUSE", "value_a": "$60M",
                "label_b": "AFTER REUSE", "value_b": "$24M",
            },
            "emotions": ["excitement"],
            "tone": "celebratory",
            "visual_concepts": ["Rocket ascending over ocean at dawn"],
            "image_search_query": "rocket launch dawn",
            "image_generation_prompt": "A rocket ascending over the ocean at dawn, "
            "photorealistic, dramatic lighting, no text",
        }
        brief.update(self.overrides)
        return brief


def solid_png(color: str = "#3355AA", size: tuple[int, int] = (1200, 1200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


class FakeGenerator:
    def __init__(self):
        self.prompts: list[str] = []

    def generate(self, prompt: str, size: tuple[int, int]) -> bytes:
        self.prompts.append(prompt)
        return solid_png("#225577", (1024, 1024))


class FakeStock:
    def __init__(self, hit: bool = True):
        self.hit = hit
        self.queries: list[str] = []

    def search(self, query: str, size: tuple[int, int]) -> SourcedImage | None:
        self.queries.append(query)
        if not self.hit:
            return None
        return SourcedImage(
            origin=ImageOrigin.STOCK,
            data=solid_png("#775522"),
            credit="Photo: Test / Unsplash",
        )


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def fake_generator():
    return FakeGenerator()


@pytest.fixture
def fake_stock():
    return FakeStock()
