"""KnowledgeService — 知识库管理面板服务。

提供 UI 的"知识库管理"页面所需的功能：
- 上传文档触发摄取
- 列出已摄取的文档
- 按 collection 查看 chunk
- 删除文档
"""
from __future__ import annotations

from pathlib import Path

from ..rag.collections import CollectionName


class KnowledgeService:
    def ingest_file(self, file_path: str | Path, collection: CollectionName) -> dict:
        """触发摄取流水线，返回统计。"""
        # TODO: call src.rag.ingestion.pipeline.ingest
        raise NotImplementedError

    def list_documents(self, collection: CollectionName) -> list[dict]:
        """按文档维度聚合（一份 PDF 是一个文档，可能对应多个 chunk）。"""
        # TODO
        raise NotImplementedError

    def list_chunks(self, collection: CollectionName, source: str) -> list[dict]:
        """指定文档的所有 chunk 详情，UI 用于展开预览。"""
        # TODO
        raise NotImplementedError

    def delete_document(self, collection: CollectionName, source: str) -> int:
        """删除一份文档：移除该 source 的所有 chunk + BM25 索引。"""
        # TODO
        raise NotImplementedError
