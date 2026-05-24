from __future__ import annotations

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def check_extend_apps() -> str:
    gov = Governance()
    check = gov.check_action("read_extend_status", "claude_mcp")
    if not check["allowed"]:
        return f"Blocked: {check['reason']}"

    workday = WorkdayClient()
    router = AIRouter()
    apps = workday.get_extend_apps()
    failures = [a for a in apps if a.get("status") not in ["Active", "Success"]]
    if not failures:
        return f"✅ All {len(apps)} Extend apps running normally."
    output = [f"Found {len(failures)} Extend issue(s):\n"]
    for f in failures:
        a = router.analyze_failure(f)
        output.append(
            f"{'='*40}\nApp: {f.get('app_name')} v{f.get('version', '?')} — {f.get('status')}\nError: {f.get('error', 'Unknown')}\n\n{a.get('formatted_report') or a.get('primary_diagnosis')}\n"
        )
    return "\n".join(output)
