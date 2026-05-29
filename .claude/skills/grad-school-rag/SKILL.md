---
name: grad-school-rag
description: "Grad-School-Agent 项目的 RAG 检索调试辅助。帮助查看 chunk 内容、运行检索测试、对比 Dense vs Sparse 召回、调试 RRF 融合参数。Use when user says '调试 RAG', '看下检索效果', '为什么没召回', 'debug retrieval', 'tune chunk size', '调 chunk', 'BM25 vs Dense'."
---

# Grad-School-RAG — RAG 调试辅助

帮助用户调试本项目的 Hybrid RAG（详见 [`DEV_SPEC.md` 3.2 节](../../../DEV_SPEC.md#32-rag-流水线)）。

## 调试场景

| 用户问题 | 本 skill 提供的工作流 |
|---------|---------------------|
| "为什么这个 query 没召回到 XX 文档" | 拆 Dense / Sparse 各路单独跑 → 看分数 → 定位是 embedding 失败还是 BM25 关键词不匹配 |
| "Chunk 切太碎了" | 读 `data/seed/*.json` 或 raw 文档 → 实际跑 splitter → 看切出来的 chunk 分布 |
| "我想看 schools collection 里有多少 chunk" | 用 chromadb 客户端查 collection.count() 和 sample |
| "RRF 融合后排序对吗" | mock 两路输入跑 `_rrf_fuse` → 手算 RRF 分数对比 |
| "Embedding 维度对不上" | 检查 EmbeddingClient 配置 vs collection 实际维度 |

## 工作流

### 1. 准备

读：

- [`src/rag/retrieval/hybrid_search.py`](../../../src/rag/retrieval/hybrid_search.py)
- [`src/rag/retrieval/dense_retriever.py`](../../../src/rag/retrieval/dense_retriever.py)
- [`src/rag/retrieval/sparse_retriever.py`](../../../src/rag/retrieval/sparse_retriever.py)
- [`config/settings.yaml`](../../../config/settings.yaml) 的 `retrieval` 节

### 2. 单路检索快速测试

```python
# 在 Python REPL（uv run python）：
from src.rag.collections import CollectionName
from src.rag.retrieval.dense_retriever import DenseRetriever
from src.rag.retrieval.sparse_retriever import SparseRetriever

dense = DenseRetriever(CollectionName.SCHOOLS)
sparse = SparseRetriever(CollectionName.SCHOOLS)

q = "美国 CS 排名 Top 10 项目"
print("Dense top5:")
for r in dense.retrieve(q, top_k=5):
    print(f"  [{r.score:.3f}] {r.content[:80]}...")

print("Sparse top5:")
for r in sparse.retrieve(q, top_k=5):
    print(f"  [{r.score:.3f}] {r.content[:80]}...")
```

### 3. 验证融合

```python
from src.rag.retrieval.hybrid_search import HybridSearch

hybrid = HybridSearch(CollectionName.SCHOOLS, rrf_k=60)
results = hybrid.search(q, top_k_dense=10, top_k_sparse=10, top_k_final=3)
```

### 4. 检查 collection 状态

```python
from src.rag.collections import get_collection, CollectionName

col = get_collection(CollectionName.SCHOOLS)
print("总 chunk 数:", col.count())
print("样本:", col.peek(limit=3))
```

### 5. 常见调参建议

| 现象 | 调什么 |
|------|------|
| 召回粒度太细 | chunk_size 从 500 提到 800 |
| Top1 不准 | top_k_dense / top_k_sparse 各 +10，让融合候选集更大 |
| Dense 占主导 | 提高 rrf_k（弱化两路排名差异），或检查 BM25 索引是否构建 |
| BM25 完全没结果 | 检查 query 是否触发 stop word 过滤 |

## 不做什么

- 不直接改 production 代码 → 改完用 Python REPL 验证后告诉用户改什么
- 不引入新的检索算法 → reranker 是架构预留点，本期不实现
