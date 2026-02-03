import json
import requests
import datetime
from memory_system import MemorySystem

# === 1. 初始化记忆系统 ===
memory_sys = MemorySystem()

# === 2. 定义工具函数 ===

def save_to_long_term_memory(content):
    """将重要信息存入长期记忆数据库"""
    try:
        memory_sys.add_memory(content, metadata={"timestamp": datetime.datetime.now().isoformat()})
        return f"已成功将以下信息存入长期记忆库: '{content}'"
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

def get_current_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# === 3. 定义工具 Schema ===
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "save_to_long_term_memory",
            "description": "当用户提供值得永久保存的重要信息（如个人喜好、重要事实、未来计划）时调用此工具。不要存储琐碎的闲聊。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要存储的具体信息内容"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_long_term_memory",
            "description": "当用户询问过去发生的事情、个人信息或之前提到的知识时，调用此工具检索记忆。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或问题"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

available_tools = {
    "save_to_long_term_memory": save_to_long_term_memory,
    "query_long_term_memory": query_long_term_memory,
    "get_current_time": get_current_time
}

class RAGAgent:
    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434"):
        self.model = model
        self.api_url = f"{base_url}/api/chat"
        # 优化提示词，让模型更倾向于在回答“我是谁”这类问题前先查数据库
        self.history = [
            {"role": "system", "content": """你是一个拥有长期记忆能力的智能助手。
你的核心能力是可以自主决定将信息存入“长期记忆数据库”或从库中检索信息。

决策逻辑：
1. **存储决策**：当用户提到重要信息（如名字、职业、喜好、待办事项、重要知识）时，请务必调用 `save_to_long_term_memory`。对于简单的问候或闲聊，不要存储。
2. **检索决策**：当用户问的问题涉及**过去的历史**、**个人身份**（如“我是谁”）、**偏好**或**之前提到的知识**时，你**必须**先调用 `query_long_term_memory` 检索相关信息，然后再回答。

**回答原则**：
- 当你获得检索到的记忆时，请**不要**机械地复述所有信息。
- 你需要**推理**用户的意图，只从记忆中提取与当前问题**真正相关**的部分进行回答。
- 如果记忆中包含零碎或不相关的信息，请自动忽略。
- 用自然、流畅的对话语气回答，就像老朋友聊天一样，不要暴露“我检索到了...”这样的技术细节。"""}
        ]

    def chat(self, user_input):
        self.history.append({"role": "user", "content": user_input})

        # --- 强制检索逻辑 (Heuristic) ---
        # 如果用户问 "我是谁"、"我叫什么"、"你记得..."，强制触发一次检索
        # 这样可以弥补模型有时“偷懒”不调用工具的问题
        forced_context = ""
        keywords = ["我是谁", "我叫什么", "我的名字", "你记得", "我喜欢"]
        if any(k in user_input for k in keywords):
            print("  [系统] 检测到记忆相关问题，正在自动检索...")
            memories = query_long_term_memory(user_input)
            forced_context = f"""
[系统隐式提示]
以下是从长期记忆库中检索到的相关片段（可能包含不相关或过时的信息，请利用你的逻辑能力进行筛选和整合）：
---
{memories}
---
请仅基于以上信息中与用户问题 "{user_input}" 相关的部分进行回答。
忽略不相关的碎片信息。请用自然的人性化语气回答。
"""
            # 将检索结果作为系统消息临时插入
            self.history.append({"role": "system", "content": forced_context})

        payload = {
            "model": self.model,
            "messages": self.history,
            "tools": tools_schema,
            "stream": False
        }

        try:
            print("Agent (思考中)...")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})
            
            # 处理工具调用
            if message.get("tool_calls"):
                self.history.append(message)
                for tool in message["tool_calls"]:
                    func_name = tool["function"]["name"]
                    args = tool["function"]["arguments"]
                    print(f"  [决策] {func_name}({args})")
                    
                    if func_name in available_tools:
                        result = available_tools[func_name](**args)
                        self.history.append({"role": "tool", "content": str(result)})
                        print(f"  [记忆系统] {str(result)}")
                
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

def main():
    print("=== 本地智能体 V6 (长期记忆/RAG版) ===")
    print("记忆数据库路径: ./chroma_db")
    print("试着告诉它你的名字、喜好，然后重启程序问问它还记不记得。\n")
    
    agent = RAGAgent()
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            
            agent.chat(user_input)
            print("-" * 30)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
