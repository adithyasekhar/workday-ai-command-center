from __future__ import annotations

from datetime import datetime

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def get_tenant_health_report() -> str:
    """
    MCP Tool: Complete health report across all Workday modules.
    Includes overall status, executive summary, and issue details.
    """
    gov = Governance()
    check = gov.check_action("read_integration_status", "claude_mcp")
    if not check["allowed"]:
        gov.log_event("HEALTH_CHECK_BLOCKED", "get_tenant_health_report", "claude_mcp", check["reason"])
        return f"Blocked: {check['reason']}"

    gov.log_event("HEALTH_CHECK_STARTED", "get_tenant_health_report", "claude_mcp", "Generating tenant health report")

    workday = WorkdayClient()
    router = AIRouter()

    gov.log_event("HEALTH_FETCHING_INTEGRATIONS", "get_tenant_health_report", "claude_mcp", "Fetching integration data")
    integrations = workday.get_integration_runs()
    gov.log_event("HEALTH_INTEGRATIONS_FETCHED", "get_tenant_health_report", "claude_mcp", f"{len(integrations)} integration(s) retrieved")

    gov.log_event("HEALTH_FETCHING_PRISM", "get_tenant_health_report", "claude_mcp", "Fetching Prism data")
    prism = workday.get_prism_pipelines()
    gov.log_event("HEALTH_PRISM_FETCHED", "get_tenant_health_report", "claude_mcp", f"{len(prism)} Prism dataset(s) retrieved")

    gov.log_event("HEALTH_FETCHING_EXTEND", "get_tenant_health_report", "claude_mcp", "Fetching Extend data")
    extend = workday.get_extend_apps()
    gov.log_event("HEALTH_EXTEND_FETCHED", "get_tenant_health_report", "claude_mcp", f"{len(extend)} Extend app(s) retrieved")

    int_issues = [
        i for i in integrations
        if i.get("status") not in ["Completed", "Active", "Success"]
    ]
    prism_issues = [
        p for p in prism
        if p.get("status") not in ["Active", "Success"]
    ]
    ext_issues = [
        e for e in extend
        if e.get("status") not in ["Active", "Success"]
    ]
    total = len(int_issues) + len(prism_issues) + len(ext_issues)

    if total == 0:
        overall_status = "✅ HEALTHY"
        status_color = "GREEN"
    elif total <= 2:
        overall_status = "🟡 WARNING"
        status_color = "AMBER"
    else:
        overall_status = "🔴 CRITICAL"
        status_color = "RED"

    if total == 0:
        exec_summary = (
            "All Workday systems are operating normally. "
            "No action is required at this time."
        )
    else:
        parts = []
        if int_issues:
            parts.append(f"{len(int_issues)} integration failure(s)")
        if prism_issues:
            parts.append(f"{len(prism_issues)} Prism dataset issue(s)")
        if ext_issues:
            parts.append(f"{len(ext_issues)} Extend app error(s)")
        exec_summary = (
            f"Workday has {', '.join(parts)} requiring "
            f"immediate attention. Your HRIS team has been "
            f"alerted and fix steps are included below. "
            f"No action is needed from you until notified."
        )

    if total > 0:
        ai_report = router.generate_tenant_health_report(integrations, prism, extend)
    else:
        ai_report = "No issues to analyze."

    gov.log_event("HEALTH_CHECK_COMPLETE", "get_tenant_health_report", "claude_mcp", f"Status:{status_color} Issues:{total}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"""
{'='*55}
WORKDAY TENANT HEALTH REPORT
Generated : {timestamp}
{'='*55}

OVERALL STATUS : {overall_status}

EXECUTIVE SUMMARY (for HR Leadership):
{exec_summary}

{'─'*55}
SYSTEM BREAKDOWN:
  Integrations : {len(integrations)} total — {len(int_issues)} issue(s)
  Prism        : {len(prism)} total — {len(prism_issues)} issue(s)
  Extend Apps  : {len(extend)} total — {len(ext_issues)} issue(s)
  Total Issues : {total}

{'─'*55}
AI ANALYSIS:
{ai_report}

{'='*55}
NOTE: AI has read-only access to Workday.
All fixes must be applied by a human in Workday.
{'='*55}
"""
    return report

