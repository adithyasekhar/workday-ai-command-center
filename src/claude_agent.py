from __future__ import annotations
from typing import Any


class ClaudeAgent:
    def diagnose_failure(self, failure: dict[str, Any]) -> str:
        description = failure.get("error_message") or failure.get("error", "Unknown error")
        integration = failure.get("integration_name") or failure.get("name") or "unknown integration"
        return f"Claude diagnosis for {integration}: {description}"

    def generate_health_summary(self, issues: list[dict[str, Any]]) -> str:
        if not issues:
            return "No tenant health issues detected."
        return f"Tenant health summary: {len(issues)} issue(s) found."

    def analyze(self, question: str) -> str:
        return f"Claude quick answer: {question}"
