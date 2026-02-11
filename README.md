# Vincent Agent

这是一个基于 RAG (Retrieval-Augmented Generation) 的智能体应用，旨在提供具备领域知识问答、对话记忆和可扩展能力的 AI 助手。

## 核心功能 (Features)

- **多智能体管理 (Multi-Agent Management)**: 支持创建和配置不同的智能体，定制提示词和模型参数。
- **知识库系统 (RAG Knowledge Base)**:
  - 支持多种格式文档上传 (PDF, TXT, MD)。
  - 自动分块与向量化 (ChromaDB)。
  - **显式阈值过滤**: 基于相关性分数的质量控制，防止低相关性内容干扰。
- **智能对话 (Intelligent Chat)**:
  - **对话记忆 (Conversation Memory)**: 支持多轮对话，保持上下文连贯性。
  - **自动兜底 (Fallback Mechanism)**: 当知识库检索无结果时，自动平滑切换至通用闲聊模式。
- **现代化前端 (Modern UI)**:
  - 响应式设计，实时状态更新。
  - 模块化 JavaScript 架构。

## 业务演进路线 (Business Evolution Roadmap)

本项目遵循“从可用到卓越”的渐进式演进策略。目前处于 **阶段二** 完成状态。

- [x] **阶段一：基础检索与上下文 (Basic RAG & Context)**
  - [x] 知识库文档的增删改查与向量化。
  - [x] 基于向量相似度的语义检索。
  - [x] 多轮对话历史记忆 (Session-based Memory)。

- [x] **阶段二：质量控制与智能兜底 (Quality Control & Fallback)**
  - [x] **阈值过滤 (Threshold Filtering)**: 实现基于分数的显式过滤 (`1.0 / (1.0 + distance)`)，确保仅召回高相关性知识。
  - [x] **无缝兜底 (Graceful Fallback)**: 检索结果为空或低于阈值时，智能体自动使用基础模型能力进行通用回复，避免强行回答。

- [ ] **阶段三：智能体工具化 (Agent as a Tool User)**
  - [ ] **工具调用 (Function Calling)**: 让智能体具备使用工具的能力（如计算器、搜索工具）。
  - [ ] **API 集成**: 连接外部业务系统（如查询订单、天气、库存）。

- [ ] **阶段四：混合检索增强 (Hybrid Search & Rerank)**
  - [ ] **混合检索**: 引入 BM25 关键词检索 + 向量检索的双路召回机制，提升专有名词匹配率。
  - [ ] **重排序 (Reranking)**: 引入 Cross-Encoder 对召回结果进行精细排序，进一步提升准确性。

## 项目结构 (Project Structure)

```
vincent-agent/
├── api/                # API 路由定义 (Routes)
│   └── routes/         # 具体的业务路由 (Agent, KnowledgeBase)
├── core/               # 核心配置与常量 (Config, Enums)
├── database/           # 数据层 (Data Layer)
│   ├── db.py           # 数据库管理器 (DBManager)
│   └── models.py       # SQLAlchemy 模型定义
├── services/           # 业务逻辑层 (Service Layer)
│   ├── agent_service.py        # 智能体核心逻辑
│   ├── vector_store_service.py # 向量数据库服务
│   └── file_service.py         # 文件处理服务
├── static/             # 前端静态资源
│   ├── css/            # 样式文件
│   └── js/             # 模块化 JS (Managers, API, Utils)
├── storage/            # 文件存储目录
├── utils/              # 通用工具类
└── main.py             # 应用入口
```

## 快速开始 (Quick Start)

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

确保已配置 `config/agent.yaml` 和必要的环境变量。

### 3. 启动服务

```bash
python main.py
```

访问浏览器: `http://localhost:8000`

## 文档索引

- [系统架构文档 (Architecture)](docs/ARCHITECTURE.md)
- [向量存储指南 (Vector Store Guide)](docs/vector_store_guide.md)
