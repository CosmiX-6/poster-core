from poster_core.analysis import choose_asset_types, plan_assets, understand
from poster_core.analysis.llm import RETRY_DELAYS, GeminiChat, call_with_retries, parse_json_response
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


def test_plan_assets_carousel_narrative_deck(fake_llm):
    from poster_core.models import SlideKind

    article = Article(title="t", text="x")
    brief = understand(article, fake_llm)
    plans = plan_assets(brief, [AssetType.CAROUSEL], Platform.INSTAGRAM_POST)
    slides = plans[0].slides
    assert slides[0].kind is SlideKind.HOOK
    assert slides[0].heading == brief.hook  # cold open, not the headline
    kinds = [s.kind for s in slides]
    assert SlideKind.EVIDENCE in kinds
    assert SlideKind.MONEY_FLOW in kinds
    assert SlideKind.TIMELINE in kinds
    assert SlideKind.STATS in kinds
    assert SlideKind.COMPARISON in kinds
    assert SlideKind.QUOTE in kinds
    assert len(slides) <= 10

    # the deck always closes on a follow/CTA slide, even if that means a
    # content section (here, CONCLUSION) gets bumped by the 10-slide cap
    assert slides[-1].kind is SlideKind.CTA

    # every slide but the last carries a swipe-bait transition
    assert all(s.transition for s in slides[:-1])
    assert slides[-1].transition is None

    # no two consecutive slides share a layout
    for a, b in zip(kinds, kinds[1:]):
        assert a != b


def test_deck_without_beats_uses_summary_slide(fake_llm):
    from poster_core.models import SlideKind

    fake_llm.overrides = {"story_beats": []}
    article = Article(title="t", text="x")
    brief = understand(article, fake_llm)
    plans = plan_assets(brief, [AssetType.CAROUSEL], Platform.INSTAGRAM_POST)
    slides = plans[0].slides
    assert slides[1].kicker == "WHAT HAPPENED"
    timeline = next(s for s in slides if s.kind is SlideKind.TIMELINE)
    assert timeline.timeline[0].when == "Tuesday 09:00"


def test_thumbnail_headline_is_shortened(fake_llm):
    article = Article(title="t", text="x")
    brief = understand(article, fake_llm)
    plans = plan_assets(brief, [AssetType.THUMBNAIL], Platform.YOUTUBE_THUMBNAIL)
    assert len(plans[0].headline.split()) <= 5
    assert plans[0].subheadline is None


class _ProviderError(Exception):
    """Shaped like google-genai's APIError: the HTTP status is on `.code`."""

    def __init__(self, code: int):
        super().__init__(f"{code} from provider")
        self.code = code


def _flaky(failures: list[Exception], result="ok"):
    """A call that raises each queued error once, then returns `result`."""
    queue, calls = list(failures), []

    def call():
        calls.append(1)
        if queue:
            raise queue.pop(0)
        return result

    return call, calls


def test_retries_an_overloaded_model_until_it_answers():
    call, calls = _flaky([_ProviderError(503), _ProviderError(429)])
    slept: list[float] = []
    assert call_with_retries(call, sleep=slept.append) == "ok"
    assert len(calls) == 3 and slept == list(RETRY_DELAYS[:2])


def test_gives_up_with_the_last_error_when_the_outage_lasts():
    call, calls = _flaky([_ProviderError(503)] * 10)
    slept: list[float] = []
    with pytest.raises(_ProviderError):
        call_with_retries(call, sleep=slept.append)
    assert len(calls) == len(RETRY_DELAYS) + 1 and slept == list(RETRY_DELAYS)


@pytest.mark.parametrize("error", [_ProviderError(400), _ProviderError(401), ValueError("no status")])
def test_errors_that_will_not_clear_are_not_retried(error):
    call, calls = _flaky([error])
    slept: list[float] = []
    with pytest.raises(type(error)):
        call_with_retries(call, sleep=slept.append)
    assert len(calls) == 1 and slept == []


def test_gemini_adapter_retries_a_503(monkeypatch):
    monkeypatch.setattr("poster_core.analysis.llm.time.sleep", lambda _s: None)

    class _Models:
        calls = 0

        def generate_content(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise _ProviderError(503)
            return type("Resp", (), {"text": '{"headline": "ok"}'})()

    chat = object.__new__(GeminiChat)  # skip __init__: no SDK or key needed
    chat.model = "gemini-flash-latest"
    chat._client = type("Client", (), {"models": _Models()})()
    assert chat.complete_json("system", "user") == {"headline": "ok"}
    assert chat._client.models.calls == 2
