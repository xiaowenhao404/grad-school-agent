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
        # dense 失败时返回空，不抛
        try:
            dense_results = self.dense.retrieve(query, top_k_dense, where=where)
        except Exception:
            dense_results = []
        # sparse 失败时返回空（bm25.pkl 缺失/损坏都走这里）
        try:
            sparse_results = self.sparse.retrieve(query, top_k_sparse)
        except Exception:
            sparse_results = []
        # sparse 结果按 metadata 过滤（与 dense 保持一致）
        if where and sparse_results:
            sparse_results = _filter_by_where(sparse_results, where)
        # 都空就直接返回空
        if not dense_results and not sparse_results:
            return []
        fused = self._rrf_fuse(dense_results, sparse_results)
        return fused[:top_k_final]

    def _rrf_fuse(
        self,
        dense: list[RetrievalResult],
        sparse: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        rrf_scores: dict[str, float] = defaultdict(float)
        all_results: dict[str, RetrievalResult] = {}
        for rank, r in enumerate(dense):
            rrf_scores[r.chunk_id] += 1.0 / (self.rrf_k + rank + 1)
            all_results[r.chunk_id] = r
        for rank, r in enumerate(sparse):
            rrf_scores[r.chunk_id] += 1.0 / (self.rrf_k + rank + 1)
            if r.chunk_id not in all_results:
                all_results[r.chunk_id] = r
        sorted_ids = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
        return [
            RetrievalResult(
                chunk_id=cid,
                content=all_results[cid].content,
                metadata=all_results[cid].metadata,
                score=rrf_scores[cid],
                source="hybrid",
            )
            for cid in sorted_ids
        ]


def _filter_by_where(results: list[RetrievalResult], where: dict) -> list[RetrievalResult]:
    """对 sparse 结果做简单 metadata 过滤（仅支持 $in 和等值）。"""
    filtered = []
    for r in results:
        match = True
        for key, condition in where.items():
            val = r.metadata.get(key)
            if isinstance(condition, dict):
                if "$in" in condition and val not in condition["$in"]:
                    match = False
                    break
                if "$eq" in condition and val != condition["$eq"]:
                    match = False
                    break
            elif val != condition:
                match = False
                break
        if match:
            filtered.append(r)
    return filtered
