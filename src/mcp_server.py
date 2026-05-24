from __future__ import annotations
import asyncio

from src.governance import Governance

try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    MCP_AVAILABLE = False


async def main() -> None:
    print("=" * 55)
    print("  Workday AI Command Center — MCP Server")
    print("  Multi-AI: Claude + GPT-4 + Gemini")
    print("  Governance: ACTIVE")
    print("=" * 55)
    if not MCP_AVAILABLE:
        print("MCP server dependencies are not installed in this environment.")
        print("Install the required packages and run this module again.")
        return

    server = Server("workday-ai-command-center")
    gov = Governance()

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="get_tenant_health_report",
                description="Full AI health report — integrations + Prism + Extend. Use for daily checks.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="check_integration_failures",
                description="Check integration failures with AI diagnosis. Filter by name optionally.",
                inputSchema={"type": "object", "properties": {"integration_name": {"type": "string", "description": "Optional integration name to filter"}}},
            ),
            types.Tool(
                name="check_prism_pipelines",
                description="Check Prism Analytics dataset health.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="check_extend_apps",
                description="Check Workday Extend app health.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_audit_log",
                description="View governance audit log of all AI actions.",
                inputSchema={"type": "object", "properties": {"last_n": {"type": "integer", "description": "Number of entries (default 20)"}}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name, arguments):
        arguments = arguments or {}
        gov.log_event("TOOL_CALLED", name, "claude_desktop", str(arguments))
        try:
            if name == "get_tenant_health_report":
                from src.tools.health_report import get_tenant_health_report

                result = get_tenant_health_report()
            elif name == "check_integration_failures":
                from src.tools.integration_tool import check_integration_failures

                result = check_integration_failures(arguments.get("integration_name"))
            elif name == "check_prism_pipelines":
                from src.tools.prism_tool import check_prism_pipelines

                result = check_prism_pipelines()
            elif name == "check_extend_apps":
                from src.tools.extend_tool import check_extend_apps

                result = check_extend_apps()
            elif name == "get_audit_log":
                entries = gov.get_audit_summary(arguments.get("last_n", 20))
                result = "\n".join([
                    f"[{e['timestamp']}] {e['event_type']} — {e['action']} — {e['details']}"
                    for e in entries
                ]) or "No audit entries yet."
            else:
                result = f"Unknown tool: {name}"
        except Exception as exc:
            result = f"Error: {exc}"
        gov.log_event("TOOL_DONE", name, "claude_desktop", f"{len(result)} chars")
        return [types.TextContent(type="text", text=result)]

    async with stdio_server() as (r, w):
        await server.run(
            r,
            w,
            InitializationOptions(
                server_name="workday-ai-command-center",
                server_version="1.0.0",
                capabilities=server.get_capabilities(),
            ),
        )
