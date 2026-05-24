from __future__ import annotations
import os
from src.claude_agent import ClaudeAgent
from src.gemini_agent import GeminiAgent
from src.openai_agent import OpenAIAgent


class AIRouter:
    def __init__(self) -> None:
        self.claude = ClaudeAgent()
        self.gpt4 = OpenAIAgent()
        self.gemini = GeminiAgent()
        self.multi = os.getenv("ENABLE_MULTI_AI", "true").lower() == "true"
        print(f"[Router] Multi-AI: {'ON' if self.multi else 'OFF'}")

    def analyze_failure(self, failure: dict[str, str]) -> dict[str, str]:
        error = failure.get("error_message") or failure.get("error", "")
        category = self.gpt4.quick_classify(error)
        diagnosis = self.claude.diagnose_failure(failure)
        validation = self.gpt4.validate_diagnosis(diagnosis, failure) if self.multi else ""
        combined = (
            "PRIMARY DIAGNOSIS (Claude):\n"
            f"{diagnosis}\n\n"
            f"ERROR CATEGORY: {category}"
        )
        if validation:
            combined += (
                "\n\nVALIDATION (GPT-4):\n"
                f"{validation}"
            )
        formatted = self.gemini.format_report(combined, "failure")
        return {
            "error_category": category,
            "primary_diagnosis": diagnosis,
            "validation": validation,
            "formatted_report": formatted or diagnosis,
        }

    def generate_tenant_health_report(self, integrations: list[dict[str, str]], prism: list[dict[str, str]], extend: list[dict[str, str]]) -> str:
        all_issues = [i for i in integrations + prism + extend if i.get("status") not in ["Completed", "Active", "Success"]]
        summary = self.claude.generate_health_summary(all_issues)
        return self.gemini.format_report(summary, "tenant_health") or summary

    def quick_answer(self, question: str) -> str:
        return self.claude.analyze(question)
