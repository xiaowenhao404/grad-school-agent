"""Sparse Retrieval（BM25 关键词检索）。"""
from __future__ import annotations

import pickle
from pathlib import Path

from ..collections import CollectionName
from .dense_retriever import RetrievalResult


class SparseRetriever:
    def __init__(self, collection_name: CollectionName):
        self.collection_name = collection_name
        self._index_data: dict | None = None

    def _load_index(self) -> dict | None:
        if self._index_data is None:
            from src.utils.config_loader import load_settings
            base = Path(load_settings()["vector_store"]["persist_path"])
            pkl_path = base / self.collection_name.value / "bm25.pkl"
            try:
                with open(pkl_path, "rb") as f:
                    self._index_data = pickle.load(f)
            except (FileNotFoundError, OSError, pickle.UnpicklingError):
                # BM25 索引缺失或损坏 → 返回 None 让上层降级为 only dense
                return None
        return self._index_data

    def retrieve(self, query: str, top_k: int = 20) -> list[RetrievalResult]:
        import jieba
        import numpy as np
        data = self._load_index()
        if data is None:
            return []
        bm25 = data["bm25"]
        chunk_ids: list[str] = data["chunk_ids"]
        docs: dict = data["docs"]

        tokens = [t for t in jieba.lcut(query) if t.strip()]
        if not tokens:
            return []
        try:
            scores = bm25.get_scores(tokens)
        except Exception:
            return []
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                break
            cid = chunk_ids[idx]
            doc = docs.get(cid)
            results.append(RetrievalResult(
                chunk_id=cid,
                content=doc.text if doc else "",
                metadata=doc.metadata if doc else {},
                score=float(scores[idx]),
                source="sparse",
            ))
        return results

