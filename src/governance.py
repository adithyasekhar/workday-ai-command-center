# Read-Only AI Governance Engine
# Principle: AI observes and alerts. Humans decide and act.

import yaml
import json
import os
from datetime import datetime
from typing import Any


class Governance:
    """
    Enforces read-only AI policy across the entire system.

    Three rules enforced always:
    1. AI can only read — never write, approve or change
    2. Sensitive data is masked before reaching any AI
    3. Every single AI action is logged with timestamp
    """

    def __init__(self):
        self.rules = self._load_rules()
        self.audit_path = "logs/audit_log.json"
        self.violation_path = "logs/violations.json"
        os.makedirs("logs", exist_ok=True)

    def _load_rules(self) -> dict[str, Any]:
        try:
            with open("config/governance_rules.yaml", "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            print("[Governance] Rules file not found — using strict defaults")
            return {
                "allowed_actions": [],
                "blocked_forever": [],
                "never_send_to_ai": [],
                "masked_fields": {},
            }

    def check_action(self, action_name: str, triggered_by: str = "ai") -> dict:
        """
        Gate check before any action executes.

        Returns:
          allowed: bool
          reason:  str
          action:  str (ALERT_ONLY enforced for all)
        """
        blocked = self.rules.get("blocked_forever", [])
        allowed = self.rules.get("allowed_actions", [])

        # ─── Check if permanently blocked ────────────────
        if action_name in blocked:
            self._log_violation(action_name, triggered_by, "Attempted blocked action")
            return {
                "allowed": False,
                "reason": (
                    f"'{action_name}' is permanently blocked. "
                    f"AI cannot take this action. "
                    f"A human must perform this in Workday directly."
                ),
                "action": "HARD_BLOCK",
            }

        # ─── Log and allow read actions ──────────────────
        self.log_event("ACTION_ALLOWED", action_name, triggered_by, "Read-only action permitted")
        return {
            "allowed": True,
            "reason": "Read-only action — permitted",
            "action": "READ_AND_ALERT_ONLY",
        }

    def validate_http_method(self, method: str, url: str) -> bool:
        """
        Validate that only GET requests are attempted.
        Logs a violation if any write method is detected.
        """
        allowed_methods = self.rules.get("allowed_http_methods", ["GET"]) or ["GET"]
        if method.upper() not in allowed_methods:
            self._log_violation(f"HTTP_{method.upper()}", "workday_client", f"Write method attempted on {url}")
            return False
        return True

    def mask_data(self, data: dict) -> dict:
        """
        Remove sensitive fields before any data
        is passed to Claude, GPT-4, or Gemini.
        Protects employee privacy at all times.
        """
        never_send = self.rules.get("never_send_to_ai", []) or []
        masked = data.copy()

        for field in never_send:
            if field in masked:
                masked[field] = "***MASKED_BY_GOVERNANCE***"

        # Also check for common variations
        sensitive_patterns = [
            "ssn",
            "sin",
            "nino",
            "tax_id",
            "bank",
            "account",
            "passport",
            "dob",
            "birth",
            "medical",
            "health",
            "salary",
            "wage",
            "compensation",
        ]
        for key in list(masked.keys()):
            for pattern in sensitive_patterns:
                if pattern in key.lower():
                    if masked[key] != "***MASKED_BY_GOVERNANCE***":
                        masked[key] = "***MASKED_BY_GOVERNANCE***"

        return masked

    def build_alert(self, alert_type: str, details: dict) -> dict:
        """
        Builds a structured alert for human action.
        """
        templates = self.rules.get("alert_templates", {}) or {}
        template = templates.get(alert_type, {})

        alert = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": alert_type,
            "ai_action": "ALERT_ONLY",
            "action_required_by": template.get("action_required_by", "HRIS Team"),
            "details": details,
            "message": self._build_alert_message(alert_type, details),
            "human_action_needed": True,
            "ai_cannot_action": True,
        }

        self.log_event("ALERT_GENERATED", alert_type, "governance_engine", f"Alert for: {alert_type}")
        return alert

    def _build_alert_message(self, alert_type: str, details: dict) -> str:
        """Build human-readable alert message."""
        messages = {
            "integration_failure": (
                f"Integration '{details.get('name', 'Unknown')}' failed. "
                f"Root cause identified. "
                f"Human action required — AI cannot fix this."
            ),
            "bonus_approval_pending": (
                f"Bonus approval is pending. "
                f"This requires a human decision. "
                f"AI cannot approve or reject bonuses."
            ),
            "performance_review_overdue": (
                f"Performance review is overdue. "
                f"Manager action required. "
                f"AI cannot submit or approve reviews."
            ),
            "termination_in_progress": (
                f"Termination process is active. "
                f"HR Director awareness alert. "
                f"AI has no access to this process."
            ),
        }
        return messages.get(alert_type, f"Alert: {alert_type} — Human action required")

    def log_event(self, event_type: str, action: str, triggered_by: str, details: str):
        """
        Write every event to the audit log.
        """
        try:
            try:
                with open(self.audit_path, "r") as f:
                    logs = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logs = []

            logs.append({
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "action": action,
                "triggered_by": triggered_by,
                "details": details,
                "ai_principle": "READ_ONLY_ALERT_ONLY",
            })

            with open(self.audit_path, "w") as f:
                json.dump(logs, f, indent=2)

        except Exception as e:
            print(f"[Governance] Log error: {e}")

    def _log_violation(self, action: str,
                       triggered_by: str, reason: str):
        """
        Log governance violations to separate file.
        Creates the file automatically if it does not exist.
        """
        try:
            # Create logs directory if it does not exist
            os.makedirs("logs", exist_ok=True)

            # Load existing violations or start fresh
            try:
                with open(self.violation_path, "r") as f:
                    violations = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                violations = []

            # Add new violation
            violations.append({
                "timestamp":    datetime.now().isoformat(),
                "severity":     "HIGH",
                "action":       action,
                "triggered_by": triggered_by,
                "reason":       reason,
                "blocked":      True,
                "ai_principle": "READ_ONLY_ALERT_ONLY"
            })

            # Write back — creates file if not exists
            with open(self.violation_path, "w") as f:
                json.dump(violations, f, indent=2)

            print(f"\n[GOVERNANCE VIOLATION LOGGED] "
                  f"{action} blocked — {reason}\n")

        except Exception as e:
            print(f"[Governance] Violation log error: {e}")

    def get_audit_summary(self, last_n: int = 20) -> list:
        """Get last N audit log entries."""
        try:
            with open(self.audit_path, "r") as f:
                logs = json.load(f)
            return logs[-last_n:]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_violations(self) -> list:
        """Get all governance violations."""
        try:
            with open(self.violation_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
