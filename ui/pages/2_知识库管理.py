"""页面 2：知识库管理。

详见 DEV_SPEC.md 第 6 章、KnowledgeService。

功能：
- 按 collection（schools / teachers / internal_docs）筛选
- 文件上传触发摄取（pdf/md/json）
- 列出已摄取文档，可展开看 chunk
- 删除文档
"""
from __future__ import annotations

# import streamlit as st
# from src.rag.collections import CollectionName
# from src.services.knowledge_service import KnowledgeService


def render() -> None:
    # TODO:
    # st.title("📚 知识库管理")
    # collection = st.selectbox("选择 Collection", [...])
    # file = st.file_uploader("上传文档")
    # if file: KnowledgeService.ingest_file(...)
    # st.dataframe(KnowledgeService.list_documents(...))
    pass


render()
