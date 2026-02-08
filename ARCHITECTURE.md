# Vincent Agent 架构文档

本文档提供了 Vincent Agent 项目的架构概览。该系统被设计为一个使用 FastAPI 作为后端，以及简单的 HTML/JS 前端的检索增强生成 (RAG) 应用程序。

## 目录结构概览

```
.
├── api/                # API 路由和端点
├── config/             # 配置文件 (YAML)
├── core/               # 核心框架工具 (异常, 响应, 状态码)
├── model/              # 模型工厂 (LLM, Embedding)
├── prompts/            # 提示词模板
├── rag/                # RAG 核心组件 (数据库, 向量存储, 模型)
├── schemas/            # Pydantic 数据模型
├── services/           # 业务逻辑层
├── static/             # 前端资源
├── utils/              # 通用工具函数
├── server.py           # 应用程序入口点
└── requirements.txt    # 项目依赖
```

## 模块说明

### 1. 应用程序入口点 (`server.py`)
- **角色**: FastAPI 应用程序的主要入口点。
- **主要职责**:
  - 初始化 FastAPI 应用。
  - 注册全局异常处理器。
  - 挂载静态文件 (前端)。
  - 包含 API 路由 (例如 `knowledge_base`)。
  - 定义全局后台任务 (例如文件上传处理)。

### 2. API 层 (`api/`)
- **角色**: 定义 RESTful API 端点。
- **组件**:
  - `routes/knowledge_base.py`: 处理知识库和文档管理的 HTTP 请求。它将业务逻辑委托给 `KnowledgeBaseService`。

### 3. 服务层 (`services/`)
- **角色**: 封装业务逻辑。
- **组件**:
  - `knowledge_base_service.py`: 实现以下逻辑:
    - 创建、更新、删除和列出知识库。
    - 上传和删除文档。
    - 协调数据库管理器 (`rag.db`) 和文件系统。

### 4. RAG 核心 (`rag/`)
- **角色**: 检索增强生成系统的核心。
- **组件**:
  - `db.py`: 数据库连接和会话管理 (SQLAlchemy)。
  - `models.py`: 定义数据库架构的 ORM 模型 (例如 `KnowledgeBase`, `KnowledgeDocument`)。
  - `vector_store.py`: 管理与向量数据库 (ChromaDB) 的交互。
    - `VectoreStoreService`: 处理文档加载、拆分、嵌入和存储。
    - `MD5Manager`: 通过跟踪 MD5 哈希值来确保文件只被处理一次。

### 5. 核心工具 (`core/`)
- **角色**: 为应用程序提供基础构建块。
- **组件**:
  - `codes.py`: 定义标准化的状态码及其描述。
  - `exception.py`: 全局异常处理器，确保一致的错误响应。
  - `response.py`: 标准化的 API 响应封装器 (`BaseResponse`)，统一 API 输出格式。

### 6. 配置 (`config/`)
- **角色**: 集中配置管理。
- **文件**:
  - `agent.yaml`, `chroma.yaml`, `database.yaml`: 特定子系统的配置。

### 7. 工具 (`utils/`)
- **角色**: 共享的辅助函数。
- **组件**:
  - `config_handler.py`: 加载和管理 YAML 配置。
  - `file_handler.py`: 文件读取和 MD5 计算。
  - `logger_handler.py`: 集中日志配置。
  - `path_tool.py`: 路径操作助手。

### 8. 前端 (`static/`)
- **角色**: 用户界面。
- **组件**:
  - `index.html`: 一个单页应用 (SPA) 风格的界面，用于管理知识库和文档，通过 REST API 与后端通信。

## 数据流 (示例: 文档上传)

1.  **前端**: 用户通过 `index.html` 选择并上传文件。
2.  **API 层**: `server.py` 接收 `/upload` 的 POST 请求。
3.  **系统**:
    - 将原始文件保存到 `data/` 目录。
    - 使用 `VectoreStoreService` 触发后台任务。
4.  **RAG 层**: `VectoreStoreService`:
    - 计算文件 MD5。
    - 检查 `MD5Manager` 是否有重复。
    - 加载并拆分文本。
    - 使用模型工厂生成嵌入。
    - 将向量存储在 ChromaDB 中。

## 开发指南
- **导入风格**: 使用绝对导入 (例如 `from utils.xxx import yyy`)。
- **文档字符串**: 遵循 Google 风格，使用中文内容和英文标点符号。
