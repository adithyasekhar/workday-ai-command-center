from __future__ import annotations

from ..ai_router import AIRouter
from ..governance import Governance
from ..workday_client import WorkdayClient


def check_prism_pipelines() -> str:
    gov = Governance()
    check = gov.check_action("read_prism_status", "claude_mcp")
    if not check["allowed"]:
        return f"Blocked: {check['reason']}"

    workday = WorkdayClient()
    router = AIRouter()
    datasets = workday.get_prism_pipelines()
    failures = [d for d in datasets if d.get("status") not in ["Active", "Success"]]
    if not failures:
        return f"✅ All {len(datasets)} Prism datasets healthy."
    output = [f"Found {len(failures)} Prism issue(s):\n"]
    for f in failures:
        a = router.analyze_failure(f)
        output.append(
            f"{'='*40}\nDataset: {f.get('name')} — {f.get('status')}\nError: {f.get('error', 'Unknown')}\n\n{a.get('formatted_report') or a.get('primary_diagnosis')}\n"
        )
    return "\n".join(output)
