# 🌌 Universal Agent Runtime Kernel (UARK)

> **"Not just an agent, but a substrate for intelligence."**

UARK (Universal Agent Runtime Kernel) 是一个高度模块化、动态可配置的智能体运行基底。它不是一个被固定的单一助手，而是一个能够通过配置“变身”为任何形态的智能体容器。

通过 **Manager-Worker 编排架构**、**RAG 长期记忆** 和 **MCP 工具协议** 的深度融合，UARK 为本地 LLM 应用提供了一个强大的操作系统级内核。

🔗 **GitHub Repository**: [https://github.com/yourskenny/Universal-Agent-Runtime-Kernel](https://github.com/yourskenny/Universal-Agent-Runtime-Kernel)

## 🌟 核心理念 (Core Concepts)

-   **基底化 (Substrate)**: 系统核心不包含具体业务逻辑，完全由 `config/agents.yaml` 定义智能体的行为、人设和能力。
-   **动态进化 (Dynamic Evolution)**: 支持运行时热重载 (Hot Reload)。修改配置文件即可实时增加专家或调整技能，无需重启内核。
-   **通用编排 (Universal Orchestration)**: 内置通用的意图识别与任务分发器，能够自动适配任何自定义的专家组合。

## 🏗️ 架构概览 (Architecture)

```
UARK/
├── main.py               # 内核入口 (Kernel Entry)
├── config/               # 基因库 (DNA)
│   └── agents.yaml       # 定义智能体的配置文件
├── core/                 # 核心组件 (Core Modules)
│   ├── orchestrator.py   # 任务编排器
│   ├── agent.py          # 通用智能体运行时
│   ├── memory.py         # RAG 记忆系统 (ChromaDB)
│   ├── mcp.py            # MCP 协议客户端
│   └── server.py         # MCP 文档服务
├── scripts/              # 实用工具脚本
└── legacy_agents/        # 进化遗迹 (Archived Versions)
```

## 🚀 快速开始 (Quick Start)

### 1. 安装

```bash
git clone https://github.com/yourskenny/Universal-Agent-Runtime-Kernel.git
cd Universal-Agent-Runtime-Kernel

# 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行内核

```bash
python main.py
```

### 3. 定义你的智能体

打开 `config/agents.yaml`，你可以随心所欲地创造智能体。例如，添加一个“翻译官”：

```yaml
- name: "Translator"
  description: "中英互译专家"
  system_prompt: "你是一个翻译官。将用户输入翻译为英文。"
  collection_name: "translation_memory"
  allowed_tools: []
```

在终端输入 `reload`，你的内核瞬间就拥有了翻译能力！

## 🛠️ 技术栈 (Tech Stack)

-   **LLM Runtime**: Ollama (推荐 Qwen2.5 / Llama3)
-   **Vector Store**: ChromaDB
-   **Embedding**: SentenceTransformers (all-MiniLM-L6-v2)
-   **Protocol**: Model Context Protocol (MCP)

## 📄 License

MIT License
