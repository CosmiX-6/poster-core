"""LLM client protocol and provider adapters.

Any object with a `complete_json(system, user) -> dict` method can drive the
analysis step, which keeps the pipeline testable offline and lets host
projects plug in their own provider.
"""

from __future__ import annotations

import json
import os
import re
from typing import Protocol, runtime_checkable

from ..errors import AnalysisError


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

    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None):
        from google import genai

        self.model = model
        self._client = genai.Client(
            api_key=api_key or os.environ.get("GOOGLE_API_KEY")
        )

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._client.models.generate_content(
            model=self.model,
            contents=user,
            config={
                "system_instruction": system,
                "response_mime_type": "application/json",
            },
        )
        return parse_json_response(resp.text or "")
