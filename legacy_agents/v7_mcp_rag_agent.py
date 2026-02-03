import json
import requests
import datetime
import subprocess
import sys
import os
from memory_system import MemorySystem

# === 1. 初始化记忆系统 (本地 ChromaDB) ===
memory_sys = MemorySystem()

# === 2. 定义本地工具 (RAG 相关) ===

def save_to_long_term_memory(content):
    """将重要信息存入长期记忆数据库"""
    try:
        # 简单切片逻辑：如果内容太长，按 500 字符切分 (模拟 Chunking)
        # 实际生产中应使用 RecursiveCharacterTextSplitter
        chunk_size = 500
        if len(content) > chunk_size:
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            for chunk in chunks:
                memory_sys.add_memory(chunk, metadata={"timestamp": datetime.datetime.now().isoformat(), "source": "doc_learning"})
            return f"文档过长，已切分为 {len(chunks)} 个片段并存入长期记忆。"
        else:
            memory_sys.add_memory(content, metadata={"timestamp": datetime.datetime.now().isoformat()})
            return f"已成功将信息存入长期记忆库。"
    except Exception as e:
        return f"存储失败: {e}"

def query_long_term_memory(query):
    """从长期记忆库中检索相关信息"""
    try:
        results = memory_sys.query_memory(query, n_results=3)
        if not results:
            return "记忆库中没有找到相关信息。"
        return f"检索到的相关记忆:\n" + "\n".join([f"- {m}" for m in results])
    except Exception as e:
        return f"检索失败: {e}"

# === 3. MCP Client 集成 (连接 mcp_doc_server.py) ===

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

# === 4. Agent 主体 ===

class KnowledgeAgent:
    def __init__(self, model="qwen2.5:7b"):
        self.model = model
        self.api_url = "http://localhost:11434/api/chat"
        
        # 启动 MCP
        print("正在连接 MCP 文档服务...")
        self.mcp_client = MCPClient("mcp_doc_server.py")
        
        # 组合所有工具
        self.local_tools = {
            "save_to_long_term_memory": save_to_long_term_memory,
            "query_long_term_memory": query_long_term_memory
        }
        
        # 构建工具 Schema
        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "save_to_long_term_memory",
                    "description": "用于保存重要信息或学习到的文档内容到数据库。",
                    "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_long_term_memory",
                    "description": "用于检索数据库中的知识。",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            }
        ] + self.mcp_client.get_ollama_tools()

        self.history = [
            {"role": "system", "content": """你是一个全能知识助手。
你拥有两项核心能力：
1. **通过 MCP 读取文档**：使用 `read_document` 工具读取用户指定的 PDF/Word 文件。
2. **通过 RAG 存储知识**：使用 `save_to_long_term_memory` 将读取到的内容存入数据库。

**学习模式指令**：
当用户让你“学习”某个文件时，你必须执行以下两步操作（可以分步执行）：
1. 先调用 `read_document` 读取文件内容。
2. 拿到内容后，立即调用 `save_to_long_term_memory` 将其存入数据库。

**问答模式指令**：
当用户提问时，优先调用 `query_long_term_memory` 检索相关知识。
"""}
        ]

    def chat(self, user_input):
        self.history.append({"role": "user", "content": user_input})
        
        # 强制检索逻辑
        if "怎么" in user_input or "如何" in user_input or "是什么" in user_input:
             memories = query_long_term_memory(user_input)
             self.history.append({"role": "system", "content": f"相关知识库内容参考:\n{memories}"})

        payload = {
            "model": self.model,
            "messages": self.history,
            "tools": self.tools_schema,
            "stream": False
        }

        try:
            print("Agent (思考中)...")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})
            
            if message.get("tool_calls"):
                self.history.append(message)
                for tool in message["tool_calls"]:
                    func_name = tool["function"]["name"]
                    args = tool["function"]["arguments"]
                    print(f"  [操作] {func_name}({str(args)[:50]}...)")
                    
                    result = ""
                    if func_name in self.local_tools:
                        result = self.local_tools[func_name](**args)
                    elif func_name in self.mcp_client.tools_map:
                        result = self.mcp_client.call_tool(func_name, args)
                    
                    # === 自动学习闭环逻辑 ===
                    # 如果读取了文档或文件夹，自动将内容存入长期记忆，无需模型再次决策
                    if func_name in ["read_document", "read_folder"]:
                        print(f"  [系统] 已读取内容，长度: {len(result)} 字符。")
                        if len(result) < 100 and "错误" in result:
                            print("  [警告] 读取似乎失败，跳过存储。")
                        else:
                            print("  [系统] 正在自动将内容存入知识库 (RAG)...")
                            # 自动调用存储工具
                            save_result = save_to_long_term_memory(result)
                            result = f"读取成功，并已自动存入知识库。\n存储结果: {save_result}"
                            print(f"  [系统] {save_result}")
                    
                    self.history.append({"role": "tool", "content": str(result)})
                    if func_name not in ["read_document", "read_folder"]: # 避免重复打印太长的内容
                        print(f"  [结果] {str(result)[:50]}...")

                # 递归调用以处理后续动作 (例如 read 后 save)
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
                print(f"Agent: {message.get('content')}")
                self.history.append(message)

        except Exception as e:
            print(f"[错误] {e}")

    def close(self):
        self.mcp_client.close()

def main():
    print("=== V7 全能智能体 (MCP文档读取 + RAG知识库) ===")
    print("支持指令示例：")
    print("1. '请学习当前目录下的 data.pdf'")
    print("2. '根据你学到的知识，告诉我 data.pdf 讲了什么？'")
    
    agent = KnowledgeAgent()
    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            agent.chat(user_input)
            print("-" * 30)
    finally:
        agent.close()

if __name__ == "__main__":
    main()
