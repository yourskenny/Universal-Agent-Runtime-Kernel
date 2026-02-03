import json
import requests
import sys

class MemoryAgent:
    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/chat"
        # 初始化对话历史，可以添加一个系统提示词
        self.history = [
            {"role": "system", "content": "你是一个乐于助人的 AI 助手。"}
        ]

    def chat(self, user_input):
        """
        发送包含历史记录的对话请求
        """
        # 添加用户消息到历史
        self.history.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model,
            "messages": self.history,
            "stream": True
        }

        full_response = ""
        print("Agent: ", end="", flush=True)

        try:
            with requests.post(self.api_url, json=payload, stream=True) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        body = json.loads(line)
                        if "message" in body and "content" in body["message"]:
                            content = body["message"]["content"]
                            print(content, end="", flush=True)
                            full_response += content
                        
                        if body.get("done", False):
                            print() # 换行
            
            # 添加助手回复到历史
            self.history.append({"role": "assistant", "content": full_response})
            return full_response

        except requests.exceptions.ConnectionError:
            print("\n\n[错误] 无法连接到 Ollama 服务。")
            return None
        except Exception as e:
            print(f"\n\n[错误] 发生异常: {e}")
            return None

def main():
    print("=== 本地智能体 V2 (带记忆功能) ===")
    
    agent = MemoryAgent()
    print(f"当前模型: {agent.model}")
    print("输入 'exit', 'quit' 退出，输入 'clear' 清空记忆。\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("Bye!")
                break
            
            if user_input.lower() == "clear":
                agent.history = [{"role": "system", "content": "你是一个乐于助人的 AI 助手。"}]
                print("[记忆已清空]")
                continue

            agent.chat(user_input)
            print("-" * 30)

        except KeyboardInterrupt:
            print("\nBye!")
            break

if __name__ == "__main__":
    main()
