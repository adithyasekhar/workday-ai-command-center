from __future__ import annotations

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def check_extend_apps() -> str:
    gov = Governance()
    check = gov.check_action("read_extend_status", "claude_mcp")
    if not check["allowed"]:
        gov.log_event("EXTEND_CHECK_BLOCKED", "check_extend_apps", "claude_mcp", check["reason"])
        return f"Blocked: {check['reason']}"

    gov.log_event("EXTEND_CHECK_STARTED", "check_extend_apps", "claude_mcp", "Fetching Extend app status")

    workday = WorkdayClient()
    router = AIRouter()
    apps = workday.get_extend_apps()
    gov.log_event("EXTEND_DATA_FETCHED", "check_extend_apps", "claude_mcp", f"{len(apps)} app(s) retrieved")

    failures = [a for a in apps if a.get("status") not in ["Active", "Success"]]

    if not failures:
        gov.log_event("EXTEND_ALL_HEALTHY", "check_extend_apps", "claude_mcp", "No Extend failures found")
        return f"✅ All {len(apps)} Extend apps running normally."

    gov.log_event("EXTEND_FAILURES_FOUND", "check_extend_apps", "claude_mcp", f"{len(failures)} failure(s) detected")

    output = [f"Found {len(failures)} Extend issue(s):\n"]
    for f in failures:
        name = f.get("app_name", "Unknown")
        gov.log_event("EXTEND_FAILURE_ANALYZING", name, "claude_mcp", f"Error: {f.get('error', 'Unknown')[:100]}")

        a = router.analyze_failure(f)
        gov.log_event("EXTEND_FAILURE_ANALYZED", name, "claude_mcp", f"Category: {a.get('error_category', 'Unknown')}")

        output.append(
            f"{'='*40}\nApp: {name} v{f.get('version', '?')} — {f.get('status')}\nError: {f.get('error', 'Unknown')}\n\n{a.get('formatted_report') or a.get('primary_diagnosis')}\n"
        )

    gov.log_event("EXTEND_CHECK_COMPLETE", "check_extend_apps", "claude_mcp", f"{len(failures)} failure(s) analyzed")
    return "\n".join(output)
