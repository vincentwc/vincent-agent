# ChromaDB 阈值过滤问题技术复盘与向量数据库对比

## 1. 问题背景

在本项目中使用 ChromaDB 作为向量存储后端时，尝试使用 LangChain 的 `similarity_score_threshold` 检索模式时遇到了以下问题：
1.  **报错信息**：`UserWarning: Relevance scores must be between 0 and 1, got [(Document(...), -0.1799...)]`。相似度小于0
2.  **功能缺失**：ChromaDB 的底层 API 仅支持 Top-K 查询（返回最近的 K 个结果），原生并不支持直接传入 `score_threshold` 参数在数据库层面进行过滤。

## 2. 根本原因分析

该问题的根源在于 **距离度量（Distance Metric）** 与 **相似度分数（Similarity Score）** 定义上的差异：

1.  **ChromaDB 的默认行为**：
    *   默认使用 **L2 欧几里得距离 (Euclidean Distance)**。
    *   **特性**：数值越小表示越相似（0 表示完全相同，无上限）。
    *   **现状**：在实际检索中，不相关的文档距离通常大于 1.0（例如 1.2 或 1.5）。

2.  **LangChain 的处理逻辑**：
    *   LangChain 的 `VectorStoreRetriever` 试图将距离转换为分数。
    *   对于某些度量，默认转换逻辑可能是简单的线性减法（如 `1 - distance`）。
    *   **冲突点**：当 L2 距离为 1.2 时，计算出的分数为 `1 - 1.2 = -0.2`。
    *   **触发警告**：LangChain 强制检查分数是否在 [0, 1] 区间，负数触发了 `UserWarning`，并导致过滤逻辑失效。

## 3. 解决方案：显式后置过滤 (Explicit Post-Filtering)

为了解决此问题并实现可靠的阈值过滤，我们放弃了 LangChain 的黑盒封装，在 `VectoreStoreService` 中实现了显式的 `search` 方法。

### 3.1 核心逻辑
采用 **“召回 (Retrieve) -> 归一化 (Normalize) -> 过滤 (Filter)”** 三步走策略：

1.  **Top-K 召回**：调用 Chroma 的 `similarity_search_with_score` 获取原始结果（包含 L2 距离）。
2.  **分数归一化**：使用非线性公式将 L2 距离映射到 [0, 1] 区间。
    *   **公式**：$$ Score = \frac{1}{1 + Distance} $$
    *   **效果**：
        *   Distance = 0.0 -> Score = 1.0 (完全匹配)
        *   Distance = 1.0 -> Score = 0.5
        *   Distance -> ∞  -> Score = 0.0
3.  **阈值过滤**：遍历结果，丢弃 Score 小于 `score_threshold` 的文档。

### 3.2 代码实现示例
```python
# database/vector_store.py

def search(self, query, k=3, score_threshold=0.3):
    # 1. 获取原始距离
    docs_and_scores = self.vector_store.similarity_search_with_score(query, k=k)
    
    results = []
    for doc, distance in docs_and_scores:
        # 2. 归一化分数
        similarity = 1.0 / (1.0 + distance)
        
        # 3. 阈值过滤
        if similarity >= score_threshold:
            doc.metadata["score"] = similarity
            results.append(doc)
            
    return results
```

## 4. 主流向量数据库特性对比

为了更好地理解 ChromaDB 的定位，以下是其与 Milvus、Elasticsearch 等主流方案的对比：

| 特性 | ChromaDB | Milvus | Elasticsearch (kNN) | Faiss | PgVector |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **定位** | 轻量级、嵌入式、AI原生 | 企业级、分布式、高性能 | 搜索引擎 + 向量插件 | 核心算法库 (Lib) | PostgreSQL 插件 |
| **部署模式** | 进程内 (In-process) 或 Client/Server | 独立服务 (微服务架构) | 独立服务 | 嵌入代码中运行 | 依附于 PG 数据库 |
| **阈值过滤** | **不支持原生阈值** (需后置处理) | 支持 Range Search (半径搜索) | 支持 `min_score` 参数 | 支持 Range Search | 需 SQL `WHERE distance < x` |
| **距离度量** | L2 (默认), Cosine, IP | L2, IP, Cosine, Jaccard 等 | L2, Cosine, DotProduct | 极丰富 (L2, IP 等) | L2, Cosine, IP |
| **混合检索** | 支持简单的 Metadata 过滤 | 强 (标量+向量混合) | **极强** (全文检索+向量) | 较弱 (需 ID 映射) | **强** (SQL 关联查询) |
| **适用场景** | 开发测试、本地应用、中小规模 RAG | 大规模生产环境、海量数据 | 需要关键词与语义混合检索 | 极低延迟要求、自定义算法 | 已有 PG 技术栈、中等规模 |

### 总结建议
*   **ChromaDB** 非常适合当前的 Agent 项目，因为它无需复杂的运维，安装即用，且对 Python 生态支持极好。
*   虽然它原生不支持阈值参数，但通过上述的**后置过滤方案**完全可以弥补这一短板，且性能损耗在中小规模数据下可忽略不计。
