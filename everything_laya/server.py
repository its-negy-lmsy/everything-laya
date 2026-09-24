"""everything_laya.server - Standard Model Context Protocol (MCP) Server for Laya.

Exposes Laya's sub-30ms System-1 reflex engine directly to:
- Claude Code
- Claude Desktop
- Cursor IDE
- Windsurf / Cascade
- Roo Code / Cline
- Any MCP-compliant AI agent

Uses standard JSON-RPC 2.0 over stdio with zero required external dependencies.
Diagnostics and logs are sent to stderr to guarantee a clean stdout JSON-RPC stream.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from everything_laya.client import LayaClient, DEFAULT_LAYA_URL
from everything_laya.guard import LayaGuard
from everything_laya.winnow import LayaWinnow

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "everything-laya"
SERVER_VERSION = "0.1.0"


def log(msg: str) -> None:
    """Print log message to stderr to avoid corrupting stdout JSON-RPC channel."""
    sys.stderr.write(f"[{SERVER_NAME}] {msg}\n")
    sys.stderr.flush()


class MCPServer:
    """JSON-RPC 2.0 stdio MCP Server for Laya."""

    def __init__(self, base_url: str = DEFAULT_LAYA_URL):
        self.base_url = os.environ.get("LAYA_URL", base_url)
        self.client = LayaClient(base_url=self.base_url)
        self.guard = LayaGuard(client=self.client)
        self.winnow = LayaWinnow(client=self.client)
        self._running = True

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return the JSON Schema definitions for all available MCP tools."""
        return [
            {
                "name": "laya_check_safety",
                "description": (
                    "Sub-35ms security & action guard for autonomous tool calls and shell commands. "
                    "Instantly evaluates whether a proposed command (bash, powershell, git, sql) is safe "
                    "to execute (ALLOW), risky (WARN), or dangerous/destructive (BLOCK)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The exact shell command or tool invocation to evaluate (e.g. 'rm -rf /', 'git status', 'npm install').",
                        },
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "laya_compact_log",
                "description": (
                    "Lossless context compactor for terminal logs, test suites, and build outputs. "
                    "Filters out noise (progress bars, verbose compile info) and preserves 100% of exact "
                    "error stack traces, file paths, line numbers, and exit codes. Saves up to 90% of LLM tokens."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The raw log or console output to compact.",
                        },
                        "focus_query": {
                            "type": "string",
                            "description": "What to focus on retaining (e.g. 'error or failure', 'assertion error', 'syntax error').",
                            "default": "error or failure",
                        },
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "laya_triage",
                "description": (
                    "Sub-30ms semantic classifier and tool/intent router. Selects the best option "
                    "from a dictionary of candidates based on natural language instructions."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "The text, ticket, code snippet, or prompt to triage.",
                        },
                        "instructions": {
                            "type": "string",
                            "description": "The question or decision prompt to answer.",
                        },
                        "options": {
                            "type": "object",
                            "description": "Key-value mapping of candidate option names to descriptions (e.g. {'bug': 'crash or error', 'feature': 'new capability'}).",
                        },
                    },
                    "required": ["state", "instructions", "options"],
                },
            },
            {
                "name": "laya_noul",
                "description": (
                    "Sub-25ms binary reflex decision (True or False) with confidence probability."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "The context or text being evaluated.",
                        },
                        "instructions": {
                            "type": "string",
                            "description": "The yes/no question to ask (e.g. 'Does this contain an unhandled exception?').",
                        },
                    },
                    "required": ["state", "instructions"],
                },
            },
            {
                "name": "laya_predict",
                "description": (
                    "Raw access to Laya ModernBERT System-1 multi-head reflex inference engine. "
                    "Supports arbitrary state and multi-head question schemas (choice, score, noul)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "description": "Input context (string, dict, or list).",
                        },
                        "questions": {
                            "type": "object",
                            "description": "Laya questions schema definition dict.",
                        },
                        "model": {
                            "type": "string",
                            "description": "Laya model variant (e.g. 'english', 'multilingual').",
                            "default": "english",
                        },
                    },
                    "required": ["state", "questions"],
                },
            },
        ]

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute the requested tool and return markdown/text string result."""
        if name == "laya_check_safety":
            command = arguments.get("command", "")
            decision = self.guard.check(command)
            return json.dumps(decision.to_dict(), indent=2)

        elif name == "laya_compact_log":
            text = arguments.get("text", "")
            focus = arguments.get("focus_query", "error or failure")
            result = self.winnow.compact(text, focus_query=focus)
            return result.text

        elif name == "laya_triage":
            state = arguments.get("state", "")
            instructions = arguments.get("instructions", "")
            options = arguments.get("options", {})
            choice, conf = self.client.choose(state, instructions, options)
            return json.dumps({
                "choice": choice,
                "confidence": round(conf, 4),
                "options": list(options.keys()),
            }, indent=2)

        elif name == "laya_noul":
            state = arguments.get("state", "")
            instructions = arguments.get("instructions", "")
            val, conf = self.client.noul(state, instructions)
            return json.dumps({
                "result": val,
                "confidence": round(conf, 4),
            }, indent=2)

        elif name == "laya_predict":
            state = arguments.get("state", "")
            questions = arguments.get("questions", {})
            model = arguments.get("model", "english")
            res = self.client.predict(state, questions, model=model)
            return json.dumps(res, indent=2)

        else:
            raise ValueError(f"Unknown tool: '{name}'")

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single JSON-RPC 2.0 request or notification."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                },
            }

        elif method in ("notifications/initialized", "initialized"):
            # Client handshake notification, no response required
            log("Client initialized successfully.")
            return None

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {},
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.get_tool_definitions(),
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result_text = self.execute_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result_text,
                            }
                        ],
                        "isError": False,
                    },
                }
            except Exception as e:
                log(f"Tool execution error on '{tool_name}': {e}\n{traceback.format_exc()}")
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error executing tool '{tool_name}': {e}",
                            }
                        ],
                        "isError": True,
                    },
                }

        else:
            # Unhandled method
            if req_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            return None

    def run_stdio(self) -> None:
        """Run standard I/O loop processing JSON-RPC lines until EOF."""
        log(f"Starting {SERVER_NAME} v{SERVER_VERSION} (Backend: {self.base_url})...")
        while self._running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break  # EOF, client closed connection

                line_strip = line.strip()
                if not line_strip:
                    continue

                request = json.loads(line_strip)
                response = self.handle_request(request)

                if response is not None:
                    out = json.dumps(response)
                    sys.stdout.write(out + "\n")
                    sys.stdout.flush()

            except json.JSONDecodeError as e:
                log(f"JSON decode error: {e}")
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
            except Exception as e:
                log(f"Unexpected error: {e}\n{traceback.format_exc()}")


def main():
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()
