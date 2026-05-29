"""文档加载器。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)
    source: str = ""


def load_pdf(path: str | Path) -> list[Document]:
    import pypdf
    reader = pypdf.PdfReader(str(path))
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            docs.append(Document(
                text=text,
                metadata={"source": str(path), "doc_type": "pdf", "page": i + 1},
                source=str(path),
            ))
    return docs


def load_markdown(path: str | Path) -> list[Document]:
    text = Path(path).read_text(encoding="utf-8")
    return [Document(text=text, metadata={"source": str(path), "doc_type": "markdown"}, source=str(path))]


def load_structured_json(path: str | Path, doc_type: str) -> list[Document]:
    import json
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    docs = []
    for r in records:
        text = " ".join(str(v) for v in r.values() if v)
        docs.append(Document(text=text, metadata={"source": str(path), "doc_type": doc_type, **r}, source=str(path)))
    return docs


def load_file(path: str | Path) -> list[Document]:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return load_pdf(p)
    if p.suffix.lower() in (".md", ".txt"):
        return load_markdown(p)
    return []
