import re
import random

class RuleBasedAgent:
    def __init__(self):
        self.name = "RuleBot"
        # 定义一些简单的规则：关键词 -> 回复列表
        self.rules = {
            r"(你好|hello|hi)": ["你好！", "Hello！", "嗨，我是规则机器人。"],
            r"(名字|是谁|叫什么)": ["我是 RuleBot，一个基于规则的简单程序。", "你可以叫我 RuleBot。"],
            r"(天气|下雨)": ["我没有联网，不知道天气怎么样。", "你可以看看窗外。"],
            r"(再见|拜拜|exit|quit)": ["再见！", "Bye bye!", "下次见。"],
            r"(.*)": ["抱歉，我听不懂你在说什么。", "你能换个说法吗？", "这超出了我的定义范围。"] # 默认回复
        }

    def chat(self, user_input):
        for pattern, responses in self.rules.items():
            if re.search(pattern, user_input, re.IGNORECASE):
                return random.choice(responses)
        return "..."

def main():
    print("=== 本地智能体 V0 (无模型/规则版) ===")
    print("这是一个不依赖 AI 模型的'智能体'。")
    print("它只能根据预设的规则回答问题。\n")
    
    agent = RuleBasedAgent()
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            response = agent.chat(user_input)
            print(f"Agent: {response}")
            
            if re.search(r"(再见|拜拜|exit|quit)", user_input, re.IGNORECASE):
                break
                
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
