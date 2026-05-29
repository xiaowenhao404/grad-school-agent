"""Retriever 工厂。

按 settings.yaml 的 retrieval.hybrid.enabled 配置，返回 HybridSearch 或单路 retriever。
预留 reranker 接入点（详见 DEV_SPEC.md 10. 可扩展性）。
"""
from __future__ import annotations

from ..collections import CollectionName
from .hybrid_search import HybridSearch


def make_retriever(collection_name: CollectionName):
    """根据配置实例化 retriever。"""
    # TODO: 读 settings.retrieval.hybrid.enabled
    # if hybrid: return HybridSearch(collection_name, rrf_k=settings.retrieval.hybrid.rrf_k)
    # else: return DenseRetriever(collection_name)
    return HybridSearch(collection_name)
