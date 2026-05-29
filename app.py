"""Streamlit 入口。"""
import streamlit as st

st.set_page_config(page_title="申研选校助手", page_icon="🎓", layout="wide")
st.title("🎓 申研选校助手")
st.markdown("从左侧侧边栏选择功能页面，或直接开始对话。")
st.info("💡 首次使用请确认已运行 `python -m src.db.init_db` 初始化数据库。")
