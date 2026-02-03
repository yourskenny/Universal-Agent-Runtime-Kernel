import json
import requests
import sys

class SimpleAgent:
    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"

    def chat(self, prompt):
        """
        发送提示词给 Ollama 并获取流式响应
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True
        }

        try:
            with requests.post(self.api_url, json=payload, stream=True) as response:
                response.raise_for_status()
                
                print("Agent: ", end="", flush=True)
                full_response = ""
                
                for line in response.iter_lines():
                    if line:
                        body = json.loads(line)
                        if "response" in body:
                            content = body["response"]
                            print(content, end="", flush=True)
                            full_response += content
                        
                        if body.get("done", False):
                            print() # 换行
                            
                return full_response

        except requests.exceptions.ConnectionError:
            print("\n\n[错误] 无法连接到 Ollama 服务。请确保 Ollama 已安装并在运行中。")
            print("下载地址: https://ollama.com/")
            return None
        except Exception as e:
            print(f"\n\n[错误] 发生异常: {e}")
            return None

def main():
    print("=== 本地智能体 V1 (基础对话版) ===")
    print("正在检查 Ollama 连接...")
    
    # 简单的连接测试
    agent = SimpleAgent()
    
    print(f"当前使用模型: {agent.model}")
    print("输入 'exit' 或 'quit' 退出对话。\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("Bye!")
                break

            agent.chat(user_input)
            print("-" * 30)

        except KeyboardInterrupt:
            print("\nBye!")
            break

if __name__ == "__main__":
    main()
