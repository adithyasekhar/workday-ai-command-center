from __future__ import annotations
import os
from typing import Any

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:  # pragma: no cover
    OPENAI_OK = False


class OpenAIAgent:
    def __init__(self) -> None:
        key = os.getenv("OPENAI_API_KEY", "")
        self.available = OPENAI_OK and bool(key) and not key.startswith("sk-paste")
        self.client = OpenAI(api_key=key) if self.available else None
        self.model = "gpt-4o-mini"

        if not self.available:
            print("[GPT-4] Not available - skipping validation")

    def validate_diagnosis(self, diagnosis: str, failure: dict[str, Any]) -> str:
        if not self.available or self.client is None:
            return "GPT-4 validation skipped - API key not configured"
        try:
            content = (
                "Review this Workday diagnosis in 3-5 sentences. Agree/disagree with root cause, "
                "add anything missed.\n\n"
                f"Error: {failure.get('error_message') or failure.get('error', '')}\n\n"
                f"Diagnosis:\n{diagnosis}"
            )
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=300,
            )
            return r.choices[0].message.content
        except Exception as exc:
            return f"GPT-4 unavailable: {exc}"

    def quick_classify(self, error: str) -> str:
        if not self.available or self.client is None:
            return "UNKNOWN"
        try:
            content = (
                "Classify this error in ONE word: NETWORK/CREDENTIALS/SCHEMA/TIMEOUT/PERMISSIONS/DATA/UNKNOWN\n\n"
                f"Error: {error}\n\n"
                "Reply with ONLY the category word."
            )
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=10,
            )
            return r.choices[0].message.content.strip()
        except Exception:
            return "UNKNOWN"
