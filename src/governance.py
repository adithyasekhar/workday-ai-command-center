from __future__ import annotations
from typing import Any


class Governance:
    def check_policies(self) -> str:
        return 'Governance check passed'

    def check_action(self, action: str, actor: str) -> dict[str, Any]:
        return {"allowed": True, "reason": ""}

    def log_event(self, event_type: str, action: str, actor: str, details: str) -> None:
        return None

    def get_audit_summary(self, last_n: int = 20) -> list[dict[str, str]]:
        return []
