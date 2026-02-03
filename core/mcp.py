import json
import subprocess
import sys

class MCPClient:
    def __init__(self, script_path):
        self.process = subprocess.Popen(
            [sys.executable, script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1
        )
        self.tools_map = {}
        self._initialize()

    def _send_rpc(self, method, params=None):
        request = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params: request["params"] = params
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())

    def _initialize(self):
        self._send_rpc("initialize")
        response = self._send_rpc("tools/list")
        for tool in response.get("result", {}).get("tools", []):
            self.tools_map[tool['name']] = tool

    def call_tool(self, name, args):
        response = self._send_rpc("tools/call", {"name": name, "arguments": args})
        if "result" in response and "content" in response["result"]:
            return response["result"]["content"][0]["text"]
        return "Tool execution failed"

    def get_ollama_tools(self):
        return [{
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        } for name, tool in self.tools_map.items()]

    def close(self):
        self.process.terminate()
