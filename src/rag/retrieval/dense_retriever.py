"""Dense Retrieval（向量检索）。

通过 Chroma collection 做 cosine similarity 检索。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..collections import CollectionName, get_collection


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
        from src.llm.embedding_client import EmbeddingClient
        from src.utils.config_loader import load_settings
        cfg = load_settings()["embedding"]
        emb = EmbeddingClient(
            provider=cfg.get("provider", "local"),
            model=cfg.get("model", ""),
            api_key=cfg.get("api_key"),
            base_url=cfg.get("base_url"),
            local_model_name=cfg.get("local_model_name"),
            batch_size=cfg.get("batch_size", 32),
        )
        vector = emb.embed([query])[0]
        col = get_collection(self.collection_name)
        kw: dict = {"query_embeddings": [vector], "n_results": min(top_k, col.count() or 1)}
        if where:
            kw["where"] = where
        res = col.query(**kw)
        results = []
        for i, doc_id in enumerate(res["ids"][0]):
            dist = res["distances"][0][i] if res.get("distances") else 0.0
            results.append(RetrievalResult(
                chunk_id=doc_id,
                content=res["documents"][0][i],
                metadata=res["metadatas"][0][i] if res.get("metadatas") else {},
                score=1.0 - dist,
                source="dense",
            ))
        return results
