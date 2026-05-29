"""Hybrid Search：Dense + Sparse + RRF 融合。

详见 DEV_SPEC.md 3.2.3 节。

RRF 公式：score(d) = sum_over_retrievers( 1 / (k + rank_i(d)) )
"""
from __future__ import annotations

from collections import defaultdict

from ..collections import CollectionName
from .dense_retriever import DenseRetriever, RetrievalResult
from .sparse_retriever import SparseRetriever


class HybridSearch:
    def __init__(
        self,
        collection_name: CollectionName,
        rrf_k: int = 60,
    ):
        self.dense = DenseRetriever(collection_name)
        self.sparse = SparseRetriever(collection_name)
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k_dense: int = 20,
        top_k_sparse: int = 20,
        top_k_final: int = 5,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        """混合检索 + RRF 融合。

        Args:
            query: 查询文本
            top_k_dense / top_k_sparse: 各路召回数
            top_k_final: 最终返回数
            where: 仅作用于 dense（Chroma 原生支持）；
                   对 sparse 结果将在融合后用 Python 过滤。
        """
        # TODO:
        # dense_results = self.dense.retrieve(query, top_k_dense, where=where)
        # sparse_results = self.sparse.retrieve(query, top_k_sparse)
        # if where: 对 sparse_results 做 metadata 过滤（与 dense 一致）
        # fused = self._rrf_fuse(dense_results, sparse_results)
        # return fused[:top_k_final]
        raise NotImplementedError

    def _rrf_fuse(
        self,
        dense: list[RetrievalResult],
        sparse: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """RRF 融合两路结果。"""
        # TODO:
        # rrf_scores = defaultdict(float)
        # for rank, r in enumerate(dense): rrf_scores[r.chunk_id] += 1/(self.rrf_k + rank + 1)
        # for rank, r in enumerate(sparse): rrf_scores[r.chunk_id] += 1/(self.rrf_k + rank + 1)
        # 重组 RetrievalResult 并按 rrf_scores 降序返回
        raise NotImplementedError
