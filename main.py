import argparse
import asyncio
import os
import sys

from src.mcp_server import main as server_main


def run_local_fallback() -> None:
    print("Workday AI Command Center local fallback")
    print("The MCP stdio server will not start in this environment.")
    print()
    print("Use this runner when a local terminal-only execution is required.")
    print("Set LOCAL_FALLBACK=false or omit --local to attempt launching the MCP server.")
    print()
    print("Example:")
    print("  python main.py --local")
    print("  LOCAL_FALLBACK=true python main.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Workday AI Command Center")
    parser.add_argument("--local", action="store_true", help="Run local fallback instead of starting the MCP server")
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    local_fallback = args.local or os.getenv("LOCAL_FALLBACK", "false").lower() in ("1", "true", "yes")
    if local_fallback:
        run_local_fallback()
        sys.exit(0)

    try:
        asyncio.run(server_main())
    except Exception as exc:
        print("Unable to start the MCP stdio server. Falling back to local runner.")
        print(f"Error: {exc}")
        print()
        run_local_fallback()
