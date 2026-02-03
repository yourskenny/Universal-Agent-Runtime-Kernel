import yaml
import sys
import os
from core.memory import MemorySystem
from core.mcp import MCPClient
from core.agent import GenericAgent
from core.orchestrator import Orchestrator

def load_config(path="config/agents.yaml"):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    print("=== MyAgent Framework Kernel ===")
    print("正在加载核心模块...")
    
    # 1. 初始化基础设施
    memory_sys = MemorySystem()
    # 指向 core/server.py
    server_path = os.path.join("core", "server.py")
    mcp_client = MCPClient(server_path)
    
    # 2. 加载智能体配置 (Profiles)
    print("正在加载智能体配置...")
    config = load_config()
    agents_config = config.get("agents", [])
    
    # 3. 动态实例化智能体
    agents = {}
    for agent_cfg in agents_config:
        print(f"  - 注册智能体: {agent_cfg['name']}")
        agents[agent_cfg['name']] = GenericAgent(
            name=agent_cfg['name'],
            description=agent_cfg['description'],
            system_prompt=agent_cfg['system_prompt'],
            collection_name=agent_cfg['collection_name'],
            allowed_tools=agent_cfg.get("allowed_tools", []),
            mcp_client=mcp_client,
            memory_sys=memory_sys
        )
        
    # 4. 启动编排器
    print(f"✅ 系统就绪，共加载 {len(agents)} 个智能体。")
    orchestrator = Orchestrator(agents)
    
    print("-" * 50)
    print("交互已就绪。输入 'reload' 可重新加载配置。")
    
    try:
        while True:
            user_input = input("\nYou: ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            
            # 支持热重载配置 (Growth Capability)
            if user_input.lower() == "reload":
                print("正在重载配置...")
                config = load_config()
                # 简单重载逻辑：清空并重新注册 (实际生产应更平滑)
                agents.clear()
                for agent_cfg in config.get("agents", []):
                    agents[agent_cfg['name']] = GenericAgent(
                        name=agent_cfg['name'],
                        description=agent_cfg['description'],
                        system_prompt=agent_cfg['system_prompt'],
                        collection_name=agent_cfg['collection_name'],
                        allowed_tools=agent_cfg.get("allowed_tools", []),
                        mcp_client=mcp_client,
                        memory_sys=memory_sys
                    )
                orchestrator = Orchestrator(agents)
                print("配置已更新。")
                continue
            
            orchestrator.process(user_input)
            
    finally:
        mcp_client.close()

if __name__ == "__main__":
    main()
