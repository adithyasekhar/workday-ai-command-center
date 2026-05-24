from __future__ import annotations
import os
from typing import Any

try:
    import google.generativeai as genai
    GEMINI_OK = True
except ImportError:  # pragma: no cover
    GEMINI_OK = False


class GeminiAgent:
    def __init__(self) -> None:
        key = os.getenv("GEMINI_API_KEY", "")
        self.available = GEMINI_OK and bool(key) and not key.startswith("AIza-paste")
        self.model = None

        if self.available:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            print("[Gemini] Not available - skipping formatting")

    def format_report(self, raw: str, report_type: str = "health") -> str:
        if not self.available or self.model is None:
            return raw
        try:
            prompt = (
                f"Format this Workday {report_type} report for an HR operations team. "
                "Use clear headers, bullet points, priority labels (HIGH/MEDIUM/LOW). "
                "Keep all information but make it scannable:\n\n"
                f"{raw}"
            )
            r = self.model.generate_content(prompt)
            return getattr(r, "text", str(r))
        except Exception as exc:
            print(f"[Gemini] Format error: {exc}")
            return raw

    def create_teams_message(self, analysis: str, name: str) -> str:
        if not self.available or self.model is None:
            return analysis[:400]
        try:
            prompt = (
                "Create a concise Teams alert (max 100 words) for this Workday failure. "
                "Start with urgency emoji. Include: what failed, why, one action.\n\n"
                f"Failure: {name}\nAnalysis: {analysis}"
            )
            r = self.model.generate_content(prompt)
            return getattr(r, "text", str(r))
        except Exception:
            return analysis[:400]
