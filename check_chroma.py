import os
from collections import defaultdict

import chromadb

from rag.db import db_manager
from rag.models import KnowledgeDocument
from utils.config_handler import config
from utils.logger_handler import get_logger

logger = get_logger(__name__)


def get_db_documents(kb_id: str):
    """从 PostgreSQL 获取知识库下的所有文档信息"""
    session = db_manager.get_session()
    try:
        docs = (
            session.query(KnowledgeDocument)
            .filter(KnowledgeDocument.kb_id == kb_id)
            .all()
        )
        return {doc.id: doc for doc in docs}
    finally:
        session.close()


def check_chroma_status(tenant_id: str = "default_tenant"):
    """
    检查指定租户下知识库的向量化状态
    """
    # 1. 获取 Chroma 配置
    persist_directory = config.chroma.get("persist_directory", "./chroma_db")
    collection_name = config.chroma.get("collection_name", "vincent_agent_collection")

    print(f"=== ChromaDB 向量数据检查 ===")
    print(f"存储路径: {persist_directory}")
    print(f"集合名称: {collection_name}")
    print(f"目标租户: {tenant_id}\n")

    try:
        # 连接 Chroma
        client = chromadb.PersistentClient(path=persist_directory)
        try:
            collection = client.get_collection(name=collection_name)
        except ValueError:
            print(f"[Error] 集合 '{collection_name}' 不存在，请先上传并向量化文档。")
            return

        # 2. 获取该租户下的所有知识库
        kbs = db_manager.list_knowledge_bases(tenant_id=tenant_id)
        if not kbs:
            print(f"租户 {tenant_id} 下没有找到任何知识库。")
            return

        print(f"找到 {len(kbs)} 个知识库:\n")

        for kb in kbs:
            print(f"📚 知识库: {kb.name} (ID: {kb.id})")

            # 3. 从 PG 获取该 KB 的文档列表 (作为基准)
            db_docs_map = get_db_documents(kb.id)
            if not db_docs_map:
                print(f"   - (PG数据库中无文档记录)")
                print("-" * 50)
                continue

            # 4. 从 Chroma 获取该 KB 的所有向量数据
            # 使用 where 过滤 kb_id
            chroma_results = collection.get(
                where={"kb_id": kb.id}, include=["metadatas"]
            )

            metadatas = chroma_results.get("metadatas", [])
            total_chunks = len(metadatas)

            # 聚合统计：doc_id -> chunk_count
            doc_chunk_stats = defaultdict(int)
            for meta in metadatas:
                doc_id = meta.get("doc_id")
                if doc_id:
                    doc_chunk_stats[doc_id] += 1

            # 5. 展示对比结果
            print(f"   - 数据库文档数: {len(db_docs_map)}")
            print(f"   - 向量库总分块数: {total_chunks}")
            print(f"   - 文档详情:")

            for doc_id, doc in db_docs_map.items():
                chunk_count = doc_chunk_stats.get(doc_id, 0)
                status_icon = "✅" if chunk_count > 0 else "❌"
                status_text = (
                    f"已向量化 ({chunk_count} chunks)"
                    if chunk_count > 0
                    else "未找到向量"
                )

                print(f"     {status_icon} [{doc.filename}]")
                print(f"        ID: {doc.id}")
                print(f"        状态: {doc.status} (PG) | {status_text} (Chroma)")
                if doc.error_msg:
                    print(f"        错误信息: {doc.error_msg}")

            print("-" * 50)

    except Exception as e:
        print(f"\n[Error] 检查过程中发生错误: {e}")


if __name__ == "__main__":
    check_chroma_status()
