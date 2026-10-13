"""LLM client protocol and provider adapters.

Any object with a `complete_json(system, user) -> dict` method can drive the
analysis step, which keeps the pipeline testable offline and lets host
projects plug in their own provider.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Callable, Protocol, TypeVar, runtime_checkable

from ..errors import AnalysisError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Statuses that mean "try again shortly": the model is overloaded or the
# caller is briefly rate limited. Anything else (bad key, bad request) is not
# going to change on a second attempt.
_TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})
# Seconds to wait before the 2nd, 3rd and 4th attempt.
RETRY_DELAYS = (3.0, 8.0, 20.0)


def _status_of(exc: Exception) -> int | None:
    """HTTP status carried by an SDK error (google-genai: `code`, openai: `status_code`)."""
    for name in ("code", "status_code"):
        value = getattr(exc, name, None)
        if isinstance(value, int):
            return value
    return None


def call_with_retries(
    call: Callable[[], T],
    *,
    delays: tuple[float, ...] = RETRY_DELAYS,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run `call`, retrying while the provider answers with a transient
    status. The last error is raised once the delays are used up; any other
    error is raised at once."""
    for delay in (*delays, None):
        try:
            return call()
        except Exception as exc:
            status = _status_of(exc)
            if delay is None or status not in _TRANSIENT_STATUS:
                raise
            logger.warning("LLM answered %s; retrying in %.0fs", status, delay)
            sleep(delay)
    raise AssertionError("unreachable")


@runtime_checkable
class LLMClient(Protocol):
    def complete_json(self, system: str, user: str) -> dict: ...


def parse_json_response(raw: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating code fences."""
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AnalysisError(f"LLM did not return JSON: {raw[:200]!r}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"Invalid JSON from LLM: {exc}") from exc


class OpenAIChat:
    """OpenAI chat-completions adapter (requires the `openai` extra)."""

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        return parse_json_response(resp.choices[0].message.content or "")


class GeminiChat:
    """Google Gemini adapter (requires the `gemini` extra)."""

    def __init__(self, model: str = "gemini-flash-latest", api_key: str | None = None):
        from google import genai

        self.model = model
        self._client = genai.Client(
            api_key=api_key or os.environ.get("GOOGLE_API_KEY")
        )

    def complete_json(self, system: str, user: str) -> dict:
        # The SDK does not retry by default, and "503 model is experiencing
        # high demand" is common and usually clears within seconds.
        resp = call_with_retries(
            lambda: self._client.models.generate_content(
                model=self.model,
                contents=user,
                config={
                    "system_instruction": system,
                    "response_mime_type": "application/json",
                },
            )
        )
        return parse_json_response(resp.text or "")
