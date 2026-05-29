"""RAG 检索层。

- dense_retriever.py: Chroma 向量相似度
- sparse_retriever.py: BM25 关键词检索
- hybrid_search.py: RRF 融合（详见 DEV_SPEC 3.2.3）
- retriever_factory.py: 工厂方法，按配置实例化
"""

from .hybrid_search import HybridSearch

__all__ = ["HybridSearch"]
