import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from everything_laya.server import MCPServer


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.server = MCPServer()

    def test_mcp_initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-agent", "version": "1.0.0"},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "everything-laya")
        self.assertIn("tools", resp["result"]["capabilities"])

    def test_mcp_tools_list(self):
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("laya_check_safety", tool_names)
        self.assertIn("laya_compact_log", tool_names)
        self.assertIn("laya_triage", tool_names)
        self.assertIn("laya_noul", tool_names)
        self.assertIn("laya_predict", tool_names)

    def test_mcp_tool_call_guard_block(self):
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "laya_check_safety",
                "arguments": {"command": "rm -rf /"},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp["id"], 3)
        self.assertFalse(resp["result"]["isError"])
        content_text = resp["result"]["content"][0]["text"]
        data = json.loads(content_text)
        self.assertEqual(data["disposition"], "BLOCK")
        self.assertEqual(data["risk_score"], 3)


if __name__ == "__main__":
    unittest.main()
