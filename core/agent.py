import requests
import datetime
from core.memory import MemorySystem

class GenericAgent:
    def __init__(self, name, description, system_prompt, collection_name, allowed_tools=None, model="qwen2.5:7b", mcp_client=None, memory_sys=None):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.collection_name = collection_name
        self.model = model
        self.mcp_client = mcp_client
        self.memory_sys = memory_sys
        self.history = [{"role": "system", "content": system_prompt}]
        
        self.tools_schema = []
        self.local_tools = {}
        
        # 注册基础记忆工具
        if self.memory_sys:
            self._register_memory_tools()
            
        # 注册 MCP 工具
        if self.mcp_client and allowed_tools:
            self._register_mcp_tools(allowed_tools)

    def _register_memory_tools(self):
        def save_memory(content):
            try:
                chunk_size = 500
                if len(content) > chunk_size:
                    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                    for chunk in chunks:
                        self.memory_sys.add_memory(chunk, metadata={"timestamp": datetime.datetime.now().isoformat(), "agent": self.name}, collection_name=self.collection_name)
                    return f"已将长内容切片并存入【{self.name}】的知识库。"
                else:
                    self.memory_sys.add_memory(content, metadata={"timestamp": datetime.datetime.now().isoformat(), "agent": self.name}, collection_name=self.collection_name)
                    return f"已存入【{self.name}】的知识库。"
            except Exception as e:
                return f"存储失败: {e}"

        def query_memory(query):
            try:
                results = self.memory_sys.query_memory(query, n_results=5, collection_name=self.collection_name)
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

    def _register_mcp_tools(self, allowed_tools):
        all_mcp_tools = self.mcp_client.get_ollama_tools()
        for tool in all_mcp_tools:
            if tool["function"]["name"] in allowed_tools:
                self.tools_schema.append(tool)

    def chat(self, user_input, history_context=None):
        print(f"\n🤖 [{self.name}] 接管任务...")
        
        if history_context:
            self.history.append({"role": "system", "content": f"任务背景(来自Manager): {history_context}"})
            
        self.history.append({"role": "user", "content": user_input})
        
        # 自动检索 (RAG)
        if "query_memory" in self.local_tools:
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
                    
                    # 自动闭环存储
                    if func_name in ["read_document", "read_folder"]:
                        print(f"  📥 [系统] 自动将读取内容存入 {self.collection_name}...")
                        self.local_tools["save_memory"](result)
                        result = "内容已读取并自动存入您的专属知识库。"

                    self.history.append({"role": "tool", "content": str(result)})

                # 递归获取回复
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
