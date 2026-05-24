from __future__ import annotations
from datetime import datetime

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def get_tenant_health_report() -> str:
    gov = Governance()
    check = gov.check_action("read_integration_status", "claude_mcp")
    if not check["allowed"]:
        return f"Blocked: {check['reason']}"

    workday = WorkdayClient()
    router = AIRouter()
    integrations = workday.get_integration_runs()
    prism = workday.get_prism_pipelines()
    extend = workday.get_extend_apps()
    int_fail = [i for i in integrations if i.get("status") not in ["Completed", "Active"]]
    prism_fail = [p for p in prism if p.get("status") not in ["Active", "Success"]]
    ext_fail = [e for e in extend if e.get("status") not in ["Active", "Success"]]
    total = len(int_fail) + len(prism_fail) + len(ext_fail)
    if total == 0:
        return "✅ All Workday systems healthy — no failures across integrations, Prism, or Extend."

    report = router.generate_tenant_health_report(integrations, prism, extend)
    gov.log_event("HEALTH_CHECK", "all_modules", "claude_mcp", f"{total} issues found")
    return (
        "WORKDAY TENANT HEALTH REPORT\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Integration Issues: {len(int_fail)}\n"
        f"Prism Issues: {len(prism_fail)}\n"
        f"Extend Issues: {len(ext_fail)}\n"
        f"Total: {total}\n\n"
        f"{report}"
    )
