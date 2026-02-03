import json
import requests
import datetime
import subprocess
import sys
import os
from memory_system import MemorySystem

# === 1. 初始化记忆系统 ===
memory_sys = MemorySystem()

# === 2. 基础 MCP Client (复用) ===
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

# === 3. 专精智能体基类 (Specialist Agent) ===
class SpecialistAgent:
    def __init__(self, name, description, system_prompt, collection_name, allowed_tools=None, model="qwen2.5:7b", mcp_client=None):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.collection_name = collection_name
        self.model = model
        self.mcp_client = mcp_client
        self.history = [{"role": "system", "content": system_prompt}]
        
        # 绑定工具
        self.tools_schema = []
        self.local_tools = {}
        
        # 1. 记忆工具 (绑定到特定集合)
        def save_memory(content):
            """保存知识到本专家的知识库"""
            try:
                # 简单切片
                chunk_size = 500
                if len(content) > chunk_size:
                    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                    for chunk in chunks:
                        memory_sys.add_memory(chunk, metadata={"timestamp": datetime.datetime.now().isoformat(), "agent": self.name}, collection_name=self.collection_name)
                    return f"已将长内容切片并存入【{self.name}】的知识库。"
                else:
                    memory_sys.add_memory(content, metadata={"timestamp": datetime.datetime.now().isoformat(), "agent": self.name}, collection_name=self.collection_name)
                    return f"已存入【{self.name}】的知识库。"
            except Exception as e:
                return f"存储失败: {e}"

        def query_memory(query):
            """从本专家的知识库检索"""
            try:
                results = memory_sys.query_memory(query, n_results=5, collection_name=self.collection_name)
                if not results:
                    return "我的知识库中没有相关信息。"
                return f"【{self.name}】检索到的知识:\n" + "\n".join([f"- {m}" for m in results])
            except Exception as e:
                return f"检索失败: {e}"

        self.local_tools["save_memory"] = save_memory
        self.local_tools["query_memory"] = query_memory
        
        self.tools_schema.append({
            "type": "function",
            "function": {
                "name": "save_memory",
                "description": f"将重要知识存入{self.name}的专属数据库。",
                "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}
            }
        })
        self.tools_schema.append({
            "type": "function",
            "function": {
                "name": "query_memory",
                "description": f"从{self.name}的专属数据库检索知识。",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            }
        })

        # 2. MCP 工具 (如果有)
        if mcp_client and allowed_tools:
            all_mcp_tools = mcp_client.get_ollama_tools()
            for tool in all_mcp_tools:
                if tool["function"]["name"] in allowed_tools:
                    self.tools_schema.append(tool)

    def chat(self, user_input):
        print(f"\n🤖 [{self.name}] 正在思考...")
        self.history.append({"role": "user", "content": user_input})
        
        # 强制检索 (RAG)
        memories = self.local_tools["query_memory"](user_input)
        if "没有相关信息" not in memories:
            self.history.append({"role": "system", "content": f"相关背景知识:\n{memories}"})

        payload = {
            "model": self.model,
            "messages": self.history,
            "tools": self.tools_schema,
            "stream": False
        }
        
        api_url = "http://localhost:11434/api/chat"
        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})

            if message.get("tool_calls"):
                self.history.append(message)
                for tool in message["tool_calls"]:
                    func_name = tool["function"]["name"]
                    args = tool["function"]["arguments"]
                    print(f"  🛠️ [工具] {func_name}({str(args)[:50]}...)")
                    
                    result = ""
                    if func_name in self.local_tools:
                        result = self.local_tools[func_name](**args)
                    elif self.mcp_client:
                        result = self.mcp_client.call_tool(func_name, args)
                    
                    # 自动闭环存储 (针对读取类工具)
                    if func_name in ["read_document", "read_folder"]:
                        print(f"  📥 [系统] 自动将读取内容存入 {self.collection_name}...")
                        self.local_tools["save_memory"](result)
                        result = "内容已读取并自动存入您的专属知识库。"

                    self.history.append({"role": "tool", "content": str(result)})
                    print(f"  📄 [结果] {str(result)[:50]}...")

                # 递归获取最终回复
                payload["messages"] = self.history
                response = requests.post(api_url, json=payload)
                final_msg = response.json().get("message", {}).get("content", "")
                print(f"🗣️ [{self.name}]: {final_msg}")
                self.history.append({"role": "assistant", "content": final_msg})
                return final_msg
            else:
                content = message.get("content", "")
                print(f"🗣️ [{self.name}]: {content}")
                self.history.append(message)
                return content
        except Exception as e:
            print(f"Error: {e}")
            return "发生错误"

# === 4. 路由与编排 (Router) ===
def main():
    print("正在启动多智能体系统 (Multi-Agent System)...")
    mcp_client = MCPClient("mcp_doc_server.py")
    
    # 定义专精智能体
    agents = {
        "1": SpecialistAgent(
            name="CourseTutor", 
            description="AI 课程辅导员，专注于 ai-agents-course 课程内容。",
            system_prompt="你是一名 AI 课程助教。你的任务是帮助用户理解 AI Agent 的概念。你应该只回答与课程相关的问题。你的知识库中存储了大量课程文档。",
            collection_name="ai_course_knowledge", # 独立的向量集合
            allowed_tools=["read_document", "read_folder"], # 允许它读取新教材
            mcp_client=mcp_client
        ),
        "2": SpecialistAgent(
            name="PythonExpert", 
            description="Python 编程专家，专注于代码实现和调试。",
            system_prompt="你是一名资深 Python 工程师。请直接给出高质量的代码解决方案。不要废话，直接写代码。",
            collection_name="python_snippets",
            allowed_tools=["read_document"], # 允许读取代码文件
            mcp_client=mcp_client
        ),
        "3": SpecialistAgent(
            name="ChatBot",
            description="普通聊天机器人，用于闲聊。",
            system_prompt="你是一个友好的聊天助手。",
            collection_name="general_chat",
            allowed_tools=[],
            mcp_client=mcp_client
        )
    }

    print("\n=== 🌟 多智能体路由终端 ===")
    print("检测到目前算力有限，已为您启用[专家分工模式]：")
    for k, v in agents.items():
        print(f"  [{k}] {v.name}: {v.description}")
    
    current_agent = agents["3"] # 默认
    
    try:
        while True:
            print(f"\n当前专家: 【{current_agent.name}】")
            user_input = input("You (输入 'switch' 切换专家, 'exit' 退出): ").strip()
            
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            
            if user_input.lower() == "switch":
                print("请选择专家:")
                for k, v in agents.items():
                    print(f"  {k}: {v.name}")
                choice = input("编号: ")
                if choice in agents:
                    current_agent = agents[choice]
                    print(f"✅ 已切换至 {current_agent.name}")
                continue
            
            # 路由给当前专家
            current_agent.chat(user_input)
            
    finally:
        mcp_client.close()

if __name__ == "__main__":
    main()
