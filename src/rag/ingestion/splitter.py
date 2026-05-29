"""文本切分器。"""
from __future__ import annotations

import hashlib

from .loaders import Document


def split_documents(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )
    result = []
    for doc in docs:
        chunks = splitter.split_text(doc.text)
        for idx, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{doc.source}_{idx}_{chunk[:50]}".encode()).hexdigest()
            result.append(Document(
                text=chunk,
                metadata={**doc.metadata, "chunk_index": idx, "chunk_id": chunk_id},
                source=doc.source,
            ))
    return result
