"""页面 2：知识库管理。"""
import streamlit as st

st.set_page_config(page_title="知识库管理", page_icon="📚", layout="wide")
st.title("📚 知识库管理")

from src.rag.collections import CollectionName, get_collection

# ── Collection 统计 ───────────────────────────────────────────────────────────
st.subheader("Collection 状态")
cols = st.columns(3)
for i, col_name in enumerate(CollectionName):
    try:
        col = get_collection(col_name)
        count = col.count()
    except Exception:
        count = "N/A"
    cols[i].metric(col_name.value, count, "chunks")

st.divider()

# ── 摄取 internal_docs ────────────────────────────────────────────────────────
st.subheader("摄取内部文档")
uploaded = st.file_uploader("上传 PDF 或 Markdown 文件", type=["pdf", "md", "txt"],
                             accept_multiple_files=True)
if uploaded and st.button("开始摄取", type="primary"):
    import tempfile, os
    from pathlib import Path
    from src.rag.ingestion.pipeline import ingest
    with tempfile.TemporaryDirectory() as tmp:
        for f in uploaded:
            (Path(tmp) / f.name).write_bytes(f.read())
        with st.spinner("摄取中..."):
            result = ingest(tmp, CollectionName.INTERNAL_DOCS)
    st.success(f"摄取完成：{result['chunks']} 个 chunk")

st.divider()

# ── 重新摄取 schools/teachers ─────────────────────────────────────────────────
st.subheader("从数据库重新生成 schools / teachers 向量")
c1, c2 = st.columns(2)
if c1.button("重新摄取 Schools", use_container_width=True):
    from src.rag.ingestion.pipeline import ingest
    with st.spinner("摄取 schools..."):
        r = ingest(None, CollectionName.SCHOOLS)
    st.success(f"schools: {r['chunks']} chunks")
if c2.button("重新摄取 Teachers", use_container_width=True):
    from src.rag.ingestion.pipeline import ingest
    with st.spinner("摄取 teachers..."):
        r = ingest(None, CollectionName.TEACHERS)
    st.success(f"teachers: {r['chunks']} chunks")
