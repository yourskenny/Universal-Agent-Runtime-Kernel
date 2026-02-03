import json
import requests
import subprocess
import sys
import os

# === MCP Client: 能够连接 Server 的智能体 ===

class MCPAgent:
    def __init__(self, model="my-agent:v1", base_url="http://localhost:11434"):
        self.model = model
        self.api_url = f"{base_url}/api/chat"
        self.history = []
        
        # 启动 MCP 服务器 (子进程)
        print("正在连接 MCP 服务器 (mcp_server.py)...")
        self.server_process = subprocess.Popen(
            [sys.executable, "mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            bufsize=1 # 行缓冲
        )
        
        self.tools_map = {} # 存储工具定义
        self._initialize_mcp()

    def _send_rpc(self, method, params=None):
        """发送 JSON-RPC 请求给服务器"""
        request = {
            "jsonrpc": "2.0",
            "id": 1, # 简化处理，固定 ID
            "method": method
        }
        if params:
            request["params"] = params
            
        # 写入标准输入
        self.server_process.stdin.write(json.dumps(request) + "\n")
        self.server_process.stdin.flush()
        
        # 读取标准输出
        response_line = self.server_process.stdout.readline()
        if not response_line:
            return None
        return json.loads(response_line)

    def _initialize_mcp(self):
        """初始化 MCP 连接并获取工具"""
        # 1. 发送 initialize
        self._send_rpc("initialize", {
            "clientInfo": {"name": "my-agent", "version": "1.0"},
            "protocolVersion": "2024-11-05"
        })
        
        # 2. 发送 tools/list 获取工具列表
        response = self._send_rpc("tools/list")
        tools = response.get("result", {}).get("tools", [])
        
        print(f"✅ 从 MCP 服务器发现了 {len(tools)} 个工具:")
        for t in tools:
            print(f"  - {t['name']}: {t['description']}")
            self.tools_map[t['name']] = t

    def _convert_tools_to_ollama(self):
        """将 MCP 工具格式转换为 Ollama 格式"""
        ollama_tools = []
        for name, tool_def in self.tools_map.items():
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool_def["description"],
                    "parameters": tool_def["inputSchema"]
                }
            })
        return ollama_tools

    def chat(self, user_input):
        self.history.append({"role": "user", "content": user_input})

        # 动态获取工具定义
        tools_schema = self._convert_tools_to_ollama()

        payload = {
            "model": self.model,
            "messages": self.history,
            "tools": tools_schema,
            "stream": False
        }

        try:
            print("MyAgent (MCP版) 思考中...")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})
            
            # 处理工具调用
            if message.get("tool_calls"):
                self.history.append(message)
                for tool in message["tool_calls"]:
                    func_name = tool["function"]["name"]
                    args = tool["function"]["arguments"]
                    print(f"  [MCP调用] {func_name}({args})")
                    
                    # === 关键：转发给 MCP 服务器 ===
                    mcp_response = self._send_rpc("tools/call", {
                        "name": func_name,
                        "arguments": args
                    })
                    
                    # 解析结果
                    result_content = "执行失败"
                    if mcp_response and "result" in mcp_response:
                        content_list = mcp_response["result"].get("content", [])
                        if content_list:
                            result_content = content_list[0].get("text", "")
                    elif mcp_response and "error" in mcp_response:
                        result_content = f"Error: {mcp_response['error']['message']}"
                    
                    print(f"  [MCP结果] {result_content[:50]}...")
                    self.history.append({"role": "tool", "content": result_content})
                
                # 获取最终回复
                payload["messages"] = self.history
                payload["stream"] = True
                print("Agent: ", end="", flush=True)
                full_response = ""
                with requests.post(self.api_url, json=payload, stream=True) as res:
                    for line in res.iter_lines():
                        if line:
                            content = json.loads(line).get("message", {}).get("content", "")
                            print(content, end="", flush=True)
                            full_response += content
                print()
                self.history.append({"role": "assistant", "content": full_response})
            
            else:
                content = message.get("content", "")
                print(f"Agent: {content}")
                self.history.append({"role": "assistant", "content": content})

        except Exception as e:
            print(f"[错误] {e}")

    def close(self):
        if self.server_process:
            self.server_process.terminate()

def main():
    print("=== 本地智能体 V5 (MCP 架构版) ===")
    print("架构特点：智能体(Client) <--> 协议(JSON-RPC) <--> 工具服务器(Server)")
    print("这允许你连接任何符合 MCP 标准的外部工具，而无需修改智能体代码。\n")
    
    agent = MCPAgent()
    
    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            
            agent.chat(user_input)
            print("-" * 30)
    except KeyboardInterrupt:
        pass
    finally:
        agent.close()

if __name__ == "__main__":
    main()
