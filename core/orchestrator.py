import requests
import json

class Orchestrator:
    def __init__(self, agents, model="qwen2.5:7b"):
        self.agents = agents
        self.model = model
        self.history = []
        self._build_system_prompt()
        self._build_tools()

    def _build_system_prompt(self):
        agent_descriptions = "\n".join([f"{i+1}. {name}: {agent.description}" for i, (name, agent) in enumerate(self.agents.items())])
        agent_names = ", ".join(self.agents.keys())
        
        self.history = [
            {"role": "system", "content": f"""你是一个智能体团队的管理者 (Manager)。
你的任务是根据用户的输入，判断应该将任务指派给哪位专家。

团队成员如下：
{agent_descriptions}

请仔细分析用户意图，并调用工具 `dispatch_task` 将任务指派给最合适的专家。
可选专家: {agent_names}
"""}
        ]

    def _build_tools(self):
        agent_names = list(self.agents.keys())
        self.tools_schema = [{
            "type": "function",
            "function": {
                "name": "dispatch_task",
                "description": "将任务指派给特定的专家",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "agent_name": {
                            "type": "string", 
                            "enum": agent_names,
                            "description": "专家的名字"
                        },
                        "task_description": {
                            "type": "string",
                            "description": "对用户需求的总结，将作为上下文传递给专家"
                        }
                    }, 
                    "required": ["agent_name", "task_description"]
                }
            }
        }]

    def process(self, user_input):
        print(f"\n👔 [Manager] 正在分析意图...")
        self.history.append({"role": "user", "content": user_input})
        
        payload = {
            "model": self.model,
            "messages": self.history,
            "tools": self.tools_schema,
            "tool_choice": "auto", 
            "stream": False
        }
        
        try:
            response = requests.post("http://localhost:11434/api/chat", json=payload)
            message = response.json().get("message", {})
            
            if message.get("tool_calls"):
                tool = message["tool_calls"][0]
                func_name = tool["function"]["name"]
                args = tool["function"]["arguments"]
                
                if func_name == "dispatch_task":
                    target_agent_name = args["agent_name"]
                    task_desc = args["task_description"]
                    print(f"  👉 决策: 派发给 [{target_agent_name}] (任务: {task_desc})")
                    
                    if target_agent_name in self.agents:
                        return self.agents[target_agent_name].chat(user_input, history_context=task_desc)
                    else:
                        print(f"Error: Agent {target_agent_name} not found.")
            
            print("  🤔 Manager 直接回复 (未派发):")
            print(f"Manager: {message.get('content')}")
            self.history.append(message)
            return message.get("content")
            
        except Exception as e:
            print(f"Manager Error: {e}")
            return "系统错误"
