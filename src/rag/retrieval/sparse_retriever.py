"""Sparse Retrieval（BM25 关键词检索）。

使用 rank_bm25 库，索引持久化在 data/chroma/<collection>/bm25.pkl。
"""
from __future__ import annotations

from ..collections import CollectionName
from .dense_retriever import RetrievalResult


class SparseRetriever:
    def __init__(self, collection_name: CollectionName):
        self.collection_name = collection_name
        self._index = None  # 延迟加载

    def _load_index(self):
        """从磁盘加载 BM25 索引（首次访问时）。"""
        # TODO: pickle.load(open(bm25_path, 'rb'))
        raise NotImplementedError

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[RetrievalResult]:
        """BM25 检索。

        Note: BM25 不支持 metadata 过滤（与 Dense 不同）；
              如需过滤，hybrid_search 层在融合后再做。
        """
        # TODO:
        # 1. tokenize(query) -> tokens
        # 2. self._index.get_scores(tokens) -> scores
        # 3. 取 Top-K，转 RetrievalResult
        raise NotImplementedError
