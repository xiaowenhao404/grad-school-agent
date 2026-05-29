"""Retriever 工厂。"""
from __future__ import annotations

from functools import lru_cache

from ..collections import CollectionName
from .hybrid_search import HybridSearch


@lru_cache(maxsize=8)
def get_retriever(collection_name: CollectionName) -> HybridSearch:
    from src.utils.config_loader import load_settings
    rrf_k = load_settings()["retrieval"]["hybrid"]["rrf_k"]
    return HybridSearch(collection_name, rrf_k=rrf_k)
