import json
import requests
import datetime
import math
import os

# --- 1. 定义工具函数 (新增文件操作) ---

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

def list_files(path="."):
    """列出指定目录下的文件"""
    try:
        files = os.listdir(path)
        return json.dumps(files)
    except Exception as e:
        return f"无法列出文件: {str(e)}"

def read_file(filename):
    """读取当前目录下的文件内容"""
    try:
        if not os.path.exists(filename):
            return "文件不存在"
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败: {str(e)}"

def write_file(filename, content):
    """写入内容到文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"成功写入文件: {filename}"
    except Exception as e:
        return f"写入文件失败: {str(e)}"

def delete_file(filename):
    """删除指定文件"""
    try:
        if not os.path.exists(filename):
            return "文件不存在，无法删除"
        os.remove(filename)
        return f"成功删除文件: {filename}"
    except Exception as e:
        return f"删除文件失败: {str(e)}"

# --- 2. 更新工具描述 (Schema) ---
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出当前目录下的所有文件",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "目录路径，默认为 '.'"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定文件的内容",
            "parameters": {
                "type": "object",
                "properties": {"filename": {"type": "string"}},
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建或覆盖写入文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "永久删除指定文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "要删除的文件名"}
                },
                "required": ["filename"]
            }
        }
    }
]

available_tools = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file
}

class CustomAgent:
    def __init__(self, model="my-agent:v1", base_url="http://localhost:11434"):
        self.model = model
        self.api_url = f"{base_url}/api/chat"
        # 注意：这里不需要再写 System Prompt 了，因为它已经内置在模型里了
        self.history = []

    def chat(self, user_input):
        self.history.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model,
            "messages": self.history,
            "tools": tools_schema,
            "stream": False
        }

        try:
            print("MyAgent (思考中)...")
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            message = response.json().get("message", {})
            
            # 处理工具调用
            if message.get("tool_calls"):
                self.history.append(message)
                for tool in message["tool_calls"]:
                    func_name = tool["function"]["name"]
                    args = tool["function"]["arguments"]
                    print(f"  [操作] {func_name}({args})")
                    
                    if func_name in available_tools:
                        result = available_tools[func_name](**args)
                        self.history.append({"role": "tool", "content": str(result)})
                        print(f"  [结果] {str(result)[:50]}...") # 只显示前50个字符
                
                # 获取最终回复
                payload["messages"] = self.history
                payload["stream"] = True
                print("MyAgent: ", end="", flush=True)
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
                print(f"MyAgent: {content}")
                self.history.append({"role": "assistant", "content": content})

        except Exception as e:
            print(f"[错误] {e}")

def main():
    print("=== 本地定制智能体 V4 (自定义模型 + 文件操作) ===")
    print("支持命令：创建文件、读取文件、删除文件、查询时间、计算等。\n")
    
    agent = CustomAgent()
    print(f"当前使用模型: {agent.model}")
    
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
