# MCP Tool: generate_human_alert
#
# This is the most important tool in the system.
# Instead of AI taking action — it builds a structured
# alert telling the RIGHT human what needs to be done.
# AI observes. Humans act.

from datetime import datetime
from .governance import Governance


def generate_human_alert(scenario: str, details: dict | None = None) -> str:
    """
    MCP Tool: Generate a structured human action alert.

    For every scenario where action is needed —
    instead of AI acting, this tool:
    1. Identifies what happened
    2. Identifies who needs to act
    3. Explains exactly what they need to do
    4. Logs everything for compliance
    5. Makes clear AI cannot take this action
    """
    gov = Governance()
    details = details or {}

    # Build the alert
    alert = gov.build_alert(scenario, details)

    # Format for human-friendly output
    output = f"""
{'='*55}
WORKDAY ALERT — HUMAN ACTION REQUIRED
{'='*55}
Alert Type    : {scenario.replace('_',' ').upper()}
Generated At  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
AI Action     : ALERT ONLY — no changes made
Action By     : {alert.get('action_required_by', 'HRIS Team')}
{'='*55}

{alert.get('message', '')}

DETAILS:
{_format_details(details)}

{'='*55}
IMPORTANT: AI has read-only access to Workday.
This alert was generated for your awareness.
All actions must be taken by a human in Workday.
{'='*55}
"""
    gov.log_event(
        "HUMAN_ALERT_SENT",
        scenario,
        "alert_tool",
        f"Alert generated — action required by: {alert.get('action_required_by')}",
    )
    return output


def check_pending_approvals() -> str:
    """
    READ ONLY — Surface any pending approvals
    that need human attention.
    """
    gov = Governance()
    gov.log_event(
        "PENDING_APPROVALS_CHECKED",
        "check_pending_approvals",
        "claude_mcp",
        "Read-only check of pending items",
    )

    output = """
PENDING ITEMS REQUIRING HUMAN ACTION
══════════════════════════════════════════════

The following items are pending in Workday.
AI cannot approve, reject or process any of these.
Each requires a human to log in and take action.

1. Bonus Approvals
   Status  : Pending manager approval
   Action  : Manager must log into Workday
             Compensation → Bonus Processing
   AI Role : Alert only

2. Performance Reviews
   Status  : Reviews open for current cycle
   Action  : Managers must complete in Workday
             Talent → Performance → My Team
   AI Role : Alert only

3. Termination Workflows
   Status  : Any in-progress terminations
   Action  : HR Director must complete steps
             Staffing → Terminate Employee
   AI Role : Log and alert only

══════════════════════════════════════════════
REMINDER: AI has read-only access.
All approvals must be completed by humans in Workday.
══════════════════════════════════════════════
"""
    return output


def _format_details(details: dict) -> str:
    """Format details dict into readable text."""
    if not details:
        return "No additional details provided."
    lines = []
    for key, value in details.items():
        if value and value != "***MASKED_BY_GOVERNANCE***":
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")
    return "\n".join(lines) if lines else "Details logged."
