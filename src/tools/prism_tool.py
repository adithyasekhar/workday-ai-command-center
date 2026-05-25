from __future__ import annotations

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def check_prism_pipelines() -> str:
    gov = Governance()
    check = gov.check_action("read_prism_status", "claude_mcp")
    if not check["allowed"]:
        gov.log_event("PRISM_CHECK_BLOCKED", "check_prism_pipelines", "claude_mcp", check["reason"])
        return f"Blocked: {check['reason']}"

    gov.log_event("PRISM_CHECK_STARTED", "check_prism_pipelines", "claude_mcp", "Fetching Prism dataset status")

    workday = WorkdayClient()
    router = AIRouter()
    datasets = workday.get_prism_pipelines()
    gov.log_event("PRISM_DATA_FETCHED", "check_prism_pipelines", "claude_mcp", f"{len(datasets)} dataset(s) retrieved")

    failures = [d for d in datasets if d.get("status") not in ["Active", "Success"]]

    if not failures:
        gov.log_event("PRISM_ALL_HEALTHY", "check_prism_pipelines", "claude_mcp", "No Prism failures found")
        return f"✅ All {len(datasets)} Prism datasets healthy."

    gov.log_event("PRISM_FAILURES_FOUND", "check_prism_pipelines", "claude_mcp", f"{len(failures)} failure(s) detected")

    output = [f"Found {len(failures)} Prism issue(s):\n"]
    for f in failures:
        name = f.get("name", "Unknown")
        gov.log_event("PRISM_FAILURE_ANALYZING", name, "claude_mcp", f"Error: {f.get('error', 'Unknown')[:100]}")

        a = router.analyze_failure(f)
        gov.log_event("PRISM_FAILURE_ANALYZED", name, "claude_mcp", f"Category: {a.get('error_category', 'Unknown')}")

        output.append(
            f"{'='*40}\nDataset: {name} — {f.get('status')}\nError: {f.get('error', 'Unknown')}\n\n{a.get('formatted_report') or a.get('primary_diagnosis')}\n"
        )

    gov.log_event("PRISM_CHECK_COMPLETE", "check_prism_pipelines", "claude_mcp", f"{len(failures)} failure(s) analyzed")
    return "\n".join(output)
