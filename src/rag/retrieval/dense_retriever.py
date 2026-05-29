"""Dense Retrieval（向量检索）。

通过 Chroma collection 做 cosine similarity 检索。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..collections import CollectionName


@dataclass
class RetrievalResult:
    chunk_id: str
    content: str
    metadata: dict
    score: float
    source: str  # 'dense' | 'sparse'


class DenseRetriever:
    def __init__(self, collection_name: CollectionName):
        self.collection_name = collection_name

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        """对 query 计算 embedding 并查询 Chroma collection。

        Args:
            query: 用户查询文本
            top_k: 返回前 K 个
            where: Chroma metadata 过滤条件（如 {"program_id": {"$in": [...]}})
        """
        # TODO:
        # 1. embedding_client.embed([query]) -> vector
        # 2. collection.query(query_embeddings=[vector], n_results=top_k, where=where)
        # 3. 转 RetrievalResult 列表
        raise NotImplementedError
