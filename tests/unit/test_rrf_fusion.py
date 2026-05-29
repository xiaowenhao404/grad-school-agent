"""单测：RRF 融合公式验证（最关键的单测）。"""
from __future__ import annotations

from src.rag.retrieval.dense_retriever import RetrievalResult
from src.rag.retrieval.hybrid_search import HybridSearch, _filter_by_where
from src.rag.collections import CollectionName


def _make_result(chunk_id: str, score: float = 1.0, metadata: dict | None = None) -> RetrievalResult:
    return RetrievalResult(chunk_id=chunk_id, content="", metadata=metadata or {}, score=score, source="test")


def test_rrf_fuse_ordering():
    """验证 RRF 融合后排序正确：两路都命中的 chunk 得分最高。"""
    hybrid = HybridSearch.__new__(HybridSearch)
    hybrid.rrf_k = 60

    dense = [_make_result("A"), _make_result("B"), _make_result("C")]
    sparse = [_make_result("B"), _make_result("D"), _make_result("A")]

    fused = hybrid._rrf_fuse(dense, sparse)
    ids = [r.chunk_id for r in fused]

    # A 在 dense rank=0, sparse rank=2；B 在 dense rank=1, sparse rank=0
    # A score = 1/61 + 1/63 ≈ 0.0164 + 0.0159 = 0.0323
    # B score = 1/62 + 1/61 ≈ 0.0161 + 0.0164 = 0.0325
    # B 略高于 A，两者都高于 C/D
    assert ids[0] in ("A", "B")
    assert ids[1] in ("A", "B")
    assert set(ids[:2]) == {"A", "B"}


def test_rrf_fuse_scores_positive():
    dense = [_make_result("X")]
    sparse = [_make_result("Y")]
    hybrid = HybridSearch.__new__(HybridSearch)
    hybrid.rrf_k = 60
    fused = hybrid._rrf_fuse(dense, sparse)
    assert all(r.score > 0 for r in fused)


def test_rrf_fuse_deduplication():
    """同一 chunk 在两路都出现时，结果中只有一条。"""
    hybrid = HybridSearch.__new__(HybridSearch)
    hybrid.rrf_k = 60
    dense = [_make_result("A"), _make_result("B")]
    sparse = [_make_result("A"), _make_result("C")]
    fused = hybrid._rrf_fuse(dense, sparse)
    ids = [r.chunk_id for r in fused]
    assert len(ids) == len(set(ids))  # 无重复


def test_filter_by_where_in():
    results = [
        _make_result("p1", metadata={"program_id": 1}),
        _make_result("p2", metadata={"program_id": 2}),
        _make_result("p3", metadata={"program_id": 3}),
    ]
    filtered = _filter_by_where(results, {"program_id": {"$in": [1, 3]}})
    assert {r.chunk_id for r in filtered} == {"p1", "p3"}


def test_filter_by_where_eq():
    results = [
        _make_result("t1", metadata={"chunk_type": "teacher"}),
        _make_result("s1", metadata={"chunk_type": "school_overview"}),
    ]
    filtered = _filter_by_where(results, {"chunk_type": "teacher"})
    assert len(filtered) == 1
    assert filtered[0].chunk_id == "t1"
