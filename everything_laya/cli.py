"""everything_laya.cli - Command-line interface for everything-laya."""

from __future__ import annotations

import argparse
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from everything_laya import LayaClient, LayaGuard, LayaWinnow, MCPServer, __version__


def cmd_mcp(args):
    server = MCPServer(base_url=args.url)
    server.run_stdio()


def cmd_status(args):
    client = LayaClient(base_url=args.url)
    print(f"Checking Laya daemon at {client.base_url}...")
    t0 = time.perf_counter()
    if client.is_alive():
        # Do a quick test predict
        try:
            res, conf = client.noul("System status check", "Is the system healthy?")
            ms = (time.perf_counter() - t0) * 1000.0
            print(f"  [ONLINE] Laya daemon responding in {ms:.1f}ms (Decision confidence: {conf*100:.1f}%)")
            sys.exit(0)
        except Exception as e:
            print(f"  [DEGRADED] Daemon reachable but predict failed: {e}")
            sys.exit(1)
    else:
        print(f"  [OFFLINE] Unable to connect to Laya daemon at {client.base_url}.")
        print("  Start it using: python run_server.py")
        sys.exit(1)


def cmd_guard(args):
    guard = LayaGuard(base_url=args.url)
    command = " ".join(args.command)
    res = guard.check(command)
    badge = f"[{res.disposition}]"
    print(f"{badge:<8} {res.command}")
    print(f"  Risk Level : {res.risk_score}/3 ({res.risk_label})")
    print(f"  Confidence : {res.confidence * 100:.1f}%")
    print(f"  Latency    : {res.latency_ms:.1f}ms")
    print(f"  Reason     : {res.reason}")
    if res.disposition == "BLOCK":
        sys.exit(2)
    elif res.disposition == "WARN":
        sys.exit(1)
    sys.exit(0)


def cmd_winnow(args):
    winnow = LayaWinnow(base_url=args.url)
    if args.file == "-":
        content = sys.stdin.read()
    else:
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    res = winnow.compact(content, focus_query=args.focus)
    print(res.text)


def main():
    parser = argparse.ArgumentParser(
        prog="everything-laya",
        description="Ultra-fast MCP server and developer toolkit for self-hosted Laya.",
    )
    parser.add_argument("--version", action="version", version=f"everything-laya {__version__}")
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="Laya server URL (default: http://127.0.0.1:8080)")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # MCP Server
    sub_mcp = subparsers.add_parser("mcp", help="Start Model Context Protocol (MCP) JSON-RPC stdio server")
    sub_mcp.set_defaults(func=cmd_mcp)

    # Status
    sub_status = subparsers.add_parser("status", help="Check local Laya daemon health & latency")
    sub_status.set_defaults(func=cmd_status)

    # Guard
    sub_guard = subparsers.add_parser("guard", help="Evaluate safety of a shell command or tool call")
    sub_guard.add_argument("command", nargs="+", help="The command string to evaluate")
    sub_guard.set_defaults(func=cmd_guard)

    # Winnow
    sub_winnow = subparsers.add_parser("winnow", help="Compact large logs preserving exact error traces")
    sub_winnow.add_argument("file", help="File to compact (or '-' for stdin)")
    sub_winnow.add_argument("--focus", default="error or failure", help="Target query to retain")
    sub_winnow.set_defaults(func=cmd_winnow)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
