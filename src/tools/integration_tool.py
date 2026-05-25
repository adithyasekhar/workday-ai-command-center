from __future__ import annotations

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient
from ..notifier import NotificationRouter


def check_integration_failures(integration_name: str | None = None) -> str:
    gov = Governance()
    check = gov.check_action("read_integration_status", "claude_mcp")
    if not check["allowed"]:
        gov.log_event("INTEGRATION_CHECK_BLOCKED", "check_integration_failures", "claude_mcp", check["reason"])
        return f"Blocked: {check['reason']}"

    gov.log_event("INTEGRATION_CHECK_STARTED", "check_integration_failures", "claude_mcp", f"Fetching integration status{f' (filter: {integration_name})' if integration_name else ''}")

    workday = WorkdayClient()
    router = AIRouter()
    notifier = NotificationRouter()
    runs = workday.get_integration_runs()
    gov.log_event("INTEGRATION_DATA_FETCHED", "check_integration_failures", "claude_mcp", f"{len(runs)} integration run(s) retrieved")

    if integration_name:
        runs = [r for r in runs if integration_name.lower() in r.get("integration_name", "").lower()]
        gov.log_event("INTEGRATION_FILTERED", "check_integration_failures", "claude_mcp", f"Filter '{integration_name}' applied: {len(runs)} run(s) matched")

    failures = [r for r in runs if r.get("status") not in ["Completed", "Active", "Success"]]

    if not failures:
        gov.log_event("INTEGRATION_ALL_HEALTHY", "check_integration_failures", "claude_mcp", "No integration failures found")
        notifier.send_all_clear()
        return f"✅ No integration failures found." + (f" Filter: {integration_name}" if integration_name else "")

    gov.log_event("INTEGRATION_FAILURES_FOUND", "check_integration_failures", "claude_mcp", f"{len(failures)} failure(s) detected")

    output = [f"Found {len(failures)} failure(s):\n"]
    for f in failures:
        int_name = f.get("integration_name") or "unknown_integration"
        gov.log_event("INTEGRATION_FAILURE_ANALYZING", int_name, "claude_mcp", f"Error: {f.get('error_message', 'Unknown')[:100]}")

        a = router.analyze_failure(f)
        diagnosis = str(a.get('formatted_report') or a.get('primary_diagnosis') or "")

        gov.log_event("INTEGRATION_FAILURE_ANALYZED", int_name, "claude_mcp", f"Category: {a.get('error_category', 'Unknown')}")

        # determine urgency
        urgency = "HIGH"
        if diagnosis and "medium" in diagnosis.lower():
            urgency = "MEDIUM"
        elif diagnosis and "low" in diagnosis.lower():
            urgency = "LOW"

        notify_result = notifier.send_alert(f, diagnosis, urgency)
        gov.log_event("INTEGRATION_ALERT_SENT", int_name, "claude_mcp", f"Urgency: {urgency} — Sent to: {notify_result.get('sent', [])}")

        output.append(
            f"{'='*40}\n{int_name} — {f.get('status')}\nCategory: {a.get('error_category')}\nUrgency: {urgency}\nNotified: {notify_result.get('sent', [])}\n\n{diagnosis}\n"
        )

    gov.log_event("INTEGRATION_CHECK_COMPLETE", "check_integration_failures", "claude_mcp", f"{len(failures)} failure(s) analyzed and notified")
    return "\n".join(output)
