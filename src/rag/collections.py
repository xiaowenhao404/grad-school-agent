"""3 个 Chroma collection 的初始化与访问。"""
from __future__ import annotations

from enum import Enum

import chromadb

_client: chromadb.PersistentClient | None = None


class CollectionName(str, Enum):
    SCHOOLS = "schools"
    TEACHERS = "teachers"
    INTERNAL_DOCS = "internal_docs"


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        from src.utils.config_loader import load_settings
        path = load_settings()["vector_store"]["persist_path"]
        _client = chromadb.PersistentClient(path=path)
    return _client


def get_collection(name: CollectionName):
    return get_chroma_client().get_or_create_collection(
        name=name.value,
        metadata={"hnsw:space": "cosine"},
    )


def init_all_collections() -> None:
    for name in CollectionName:
        get_collection(name)
