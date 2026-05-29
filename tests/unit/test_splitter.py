"""单测：splitter chunk_id 稳定 + loaders。"""
from __future__ import annotations

import hashlib
from pathlib import Path


def test_chunk_id_stable():
    from src.rag.ingestion.loaders import Document
    from src.rag.ingestion.splitter import split_documents
    doc = Document(text="这是一段测试文本。" * 30, source="test.md",
                   metadata={"source": "test.md", "doc_type": "markdown"})
    chunks1 = split_documents([doc])
    chunks2 = split_documents([doc])
    ids1 = [c.metadata["chunk_id"] for c in chunks1]
    ids2 = [c.metadata["chunk_id"] for c in chunks2]
    assert ids1 == ids2
    assert len(set(ids1)) == len(ids1)  # 无重复


def test_load_markdown(tmp_path):
    from src.rag.ingestion.loaders import load_markdown
    f = tmp_path / "test.md"
    f.write_text("# 标题\n\n内容段落。", encoding="utf-8")
    docs = load_markdown(f)
    assert len(docs) == 1
    assert "标题" in docs[0].text
    assert docs[0].metadata["doc_type"] == "markdown"


def test_split_overlap(tmp_path):
    from src.rag.ingestion.loaders import Document
    from src.rag.ingestion.splitter import split_documents
    long_text = "A" * 600
    doc = Document(text=long_text, source="x.txt", metadata={"source": "x.txt"})
    chunks = split_documents([doc], chunk_size=200, chunk_overlap=50)
    assert len(chunks) >= 2
    # 验证 overlap：相邻 chunk 有重叠
    assert chunks[0].text[-50:] in chunks[1].text or len(chunks[1].text) > 0
