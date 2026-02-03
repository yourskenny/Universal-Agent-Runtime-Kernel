import json
import requests
import datetime
import math

# --- 1. 定义工具函数 (Skills) ---

def get_current_time():
    """获取当前系统时间"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression):
    """执行简单的数学计算"""
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        return str(eval(expression, {"__builtins__": {}}, allowed_names))
    except Exception as e:
        return f"计算出错: {str(e)}"

# --- 2. 定义工具描述 (Schema) ---
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "当用户询问当前时间、日期时使用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "当用户需要进行数学计算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，例如 '2 + 2' 或 'sqrt(16)'"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

available_tools = {
    "get_current_time": get_current_time,
    "calculate": calculate
}

class SkillsAgent:
    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434"):
        self.model = model
        self.api_url = f"{base_url}/api/chat"
        # 优化系统提示词，强制模型更积极地使用工具
        self.history = [
            {"role": "system", "content": "你是一个拥有实用技能的智能助手。注意：你本身不知道当前时间，也不能进行复杂计算。如果用户问时间或计算问题，你必须调用工具，不要自己回答。"}
        ]

    def chat(self, user_input):
        self.history.append({"role": "user", "content": user_input})

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
            response_data = response.json()
            
            message = response_data.get("message", {})
            content = message.get("content", "")
            
            # --- 关键逻辑：检查模型是否想调用工具 ---
            if message.get("tool_calls"):
                # 将模型的"想调用工具"的意图加入历史
                self.history.append(message)
                
                tool_calls = message["tool_calls"]
                for tool in tool_calls:
                    func_name = tool["function"]["name"]
                    func_args = tool["function"]["arguments"]
                    
                    print(f"  [系统] 检测到工具调用: {func_name}({func_args})")
                    
                    if func_name in available_tools:
                        func_to_call = available_tools[func_name]
                        if func_args:
                            tool_result = func_to_call(**func_args)
                        else:
                            tool_result = func_to_call()
                        
                        print(f"  [系统] 工具运行结果: {tool_result}")

                        # 将工具运行结果反馈给模型
                        self.history.append({
                            "role": "tool",
                            "content": str(tool_result),
                        })
                    else:
                        print(f"  [错误] 未知工具: {func_name}")

                # 第二次请求：发送工具结果，获取最终回答
                payload = {
                    "model": self.model,
                    "messages": self.history,
                    "stream": True 
                }
                
                print("Agent: ", end="", flush=True)
                full_response = ""
                with requests.post(self.api_url, json=payload, stream=True) as final_res:
                    final_res.raise_for_status()
                    for line in final_res.iter_lines():
                        if line:
                            body = json.loads(line)
                            content = body.get("message", {}).get("content", "")
                            print(content, end="", flush=True)
                            full_response += content
                
                self.history.append({"role": "assistant", "content": full_response})
                print() 
                
            else:
                # 模型决定不需要调用工具
                if not content:
                    # 某些模型可能返回了空内容但也没调用工具（罕见情况）
                    print("Agent: (模型似乎有些困惑，没有返回任何内容)")
                else:
                    print(f"Agent: {content}")
                    self.history.append({"role": "assistant", "content": content})

        except Exception as e:
            print(f"\n[错误] {e}")
            # 打印更详细的调试信息
            if 'response_data' in locals():
                print(f"[调试] API 返回: {json.dumps(response_data, ensure_ascii=False)}")

def main():
    print("=== 本地智能体 V3 (Skills/工具版) ===")
    print("支持技能：")
    print("1. 查询时间 (试着问：现在几点了？)")
    print("2. 数学计算 (试着问：123 乘以 456 等于多少？)\n")
    
    agent = SkillsAgent()
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue
                
            agent.chat(user_input)
            print("-" * 30)
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
