from __future__ import annotations

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def check_integration_failures(integration_name: str | None = None) -> str:
    gov = Governance()
    check = gov.check_action("read_integration_status", "claude_mcp")
    if not check["allowed"]:
        return f"Blocked: {check['reason']}"

    workday = WorkdayClient()
    router = AIRouter()
    runs = workday.get_integration_runs()
    if integration_name:
        runs = [r for r in runs if integration_name.lower() in r.get("integration_name", "").lower()]
    failures = [r for r in runs if r.get("status") not in ["Completed", "Active", "Success"]]
    if not failures:
        return f"✅ No integration failures found." + (f" Filter: {integration_name}" if integration_name else "")
    output = [f"Found {len(failures)} failure(s):\n"]
    for f in failures:
        a = router.analyze_failure(f)
        output.append(
            f"{'='*40}\n{f.get('integration_name')} — {f.get('status')}\nCategory: {a.get('error_category')}\n\n{a.get('formatted_report') or a.get('primary_diagnosis')}\n"
        )
        gov.log_event("FAILURE_ANALYZED", f.get("integration_name"), "claude_mcp", f.get("error_message", "")[:100])
    return "\n".join(output)
