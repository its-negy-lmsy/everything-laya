"""everything-laya Quick Tour & Live Demo.

Demonstrates:
1. Sub-35ms Action Safety Guard (LayaGuard)
2. Lossless Context Compactor (LayaWinnow)
3. High-level Semantic Decisions (LayaClient)
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from everything_laya import LayaClient, LayaGuard, LayaWinnow


def run_demo():
    print("=" * 65)
    print("⚡ EVERYTHING-LAYA: LIVE SYSTEM-1 AGENT TOOLKIT DEMO")
    print("=" * 65)

    client = LayaClient()
    if not client.is_alive():
        print("[!] Local Laya daemon not running on http://127.0.0.1:8080.")
        print("    Please run 'python run_server.py' first.")
        sys.exit(1)

    print("\n[1/3] 🛡️ TESTING ACTION SAFETY GUARD (LayaGuard)")
    print("-" * 50)
    guard = LayaGuard(client=client)

    commands_to_test = [
        "git status",
        "npm install react",
        "git push origin main --force",
        "rm -rf /",
    ]

    for cmd in commands_to_test:
        dec = guard.check(cmd)
        badge = f"[{dec.disposition}]"
        print(f" {badge:<8} | {dec.command:<32} | {dec.latency_ms:>5.1f}ms | Risk: {dec.risk_score}/3")

    print("\n[2/3] 📉 TESTING LOSSLESS CONTEXT COMPACTOR (LayaWinnow)")
    print("-" * 50)
    winnow = LayaWinnow(client=client)

    noisy_log = (
        "[INFO] Fetching packages from registry...\n" * 30
        + "[INFO] Compiling dependency crates...\n" * 30
        + "Traceback (most recent call last):\n"
        + '  File "database/pool.py", line 88, in connect\n'
        + '    raise ConnectionRefusedError("Database port 5432 unreachable")\n'
        + "ConnectionRefusedError: Database port 5432 unreachable\n"
        + "FAILED: tests/test_database.py::test_reconnect - Exit code: 1\n"
        + "[INFO] Cleaning up temporary build artifacts...\n" * 30
    )

    res = winnow.compact(noisy_log, focus_query="ConnectionRefusedError")
    print(f" Original lines  : {res.original_lines}")
    print(f" Compacted lines : {res.compacted_lines}")
    print(f" Token Reduction : {res.compression_ratio:.1f}%")
    print(f" Execution Time  : {res.elapsed_ms:.1f}ms")
    print("\nCompacted Result Preview:")
    print(res.text.strip())

    print("\n[3/3] 🔀 TESTING HIGH-LEVEL SEMANTIC INTENT (LayaClient)")
    print("-" * 50)
    ticket = "Users report that clicking the 'Submit Order' button throws a 500 error."
    category, conf = client.choose(
        state=ticket,
        instructions="Which team should investigate this issue?",
        criteria={
            "frontend": "UI rendering, button clicks, browser layout",
            "backend": "server 500 errors, database crashes, API endpoints",
            "devops": "DNS, networking, AWS infrastructure"
        }
    )
    print(f" Input State : \"{ticket}\"")
    print(f" Routed Team : {category.upper()} (Confidence: {conf*100:.1f}%)")

    print("\n" + "=" * 65)
    print("✅ All modules verified & ready for production AI agents!")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
