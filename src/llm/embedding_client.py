"""Embedding 客户端。

支持两种 provider：
- 云端兼容（Qwen / OpenAI）：通过 OpenAI SDK 调 embeddings 接口
- 本地（BGE）：sentence-transformers
"""
from __future__ import annotations


class EmbeddingClient:
    def __init__(
        self,
        provider: str = "qwen",
        model: str = "text-embedding-v3",
        api_key: str | None = None,
        base_url: str | None = None,
        local_model_name: str | None = None,
        batch_size: int = 32,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.local_model_name = local_model_name
        self.batch_size = batch_size
        self._model = None  # 本地模型延迟加载

    def embed(self, texts: list[str]) -> list[list[float]]:
        """对一批文本计算向量，按 batch_size 分批。"""
        if not texts:
            return []
        if self.provider == "local":
            return self._embed_local(texts)
        return self._embed_remote(texts)

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            model_name = self.local_model_name or "BAAI/bge-small-zh-v1.5"
            self._model = SentenceTransformer(model_name)
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            vecs = self._model.encode(batch, normalize_embeddings=True)
            results.extend(vecs.tolist())
        return results

    def _embed_remote(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = client.embeddings.create(model=self.model, input=batch)
            results.extend([d.embedding for d in resp.data])
        return results
