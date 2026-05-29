"""页面 4：用户行为分析。"""
import streamlit as st
import json

st.set_page_config(page_title="用户行为分析", page_icon="📊", layout="wide")
st.title("📊 用户行为分析")

from src.db.engine import get_engine
from src.db.repositories.user_repo import UserRepository

repo = UserRepository(engine=get_engine())
profile = repo.get_profile(1)

# ── 偏好记忆开关 ──────────────────────────────────────────────────────────────
memory_on = st.toggle("启用偏好记忆", value=profile.get("memory_enabled", True))
if memory_on != profile.get("memory_enabled", True):
    repo.set_memory_enabled(1, memory_on)
    st.rerun()

st.divider()

prefs = profile.get("preferences", {})
if not prefs:
    st.info("暂无偏好记录。开始对话后系统将自动学习您的偏好。")
else:
    st.subheader("当前偏好画像")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**感兴趣的国家**：", ", ".join(prefs.get("interested_countries", [])) or "未记录")
        st.write("**感兴趣的专业**：", ", ".join(prefs.get("interested_majors", [])) or "未记录")
        st.write("**学费区间（USD）**：", str(prefs.get("tuition_range_usd", "未记录")))
    with c2:
        st.write("**QS 排名偏好**：", str(prefs.get("qs_rank_range", "未记录")))
        st.write("**老师性别偏好**：", prefs.get("gender_preference_for_teacher") or "无偏好")
        st.write("**关键词**：", ", ".join(prefs.get("keywords", [])) or "未记录")

    st.subheader("原始 JSON")
    st.json(prefs)

    if st.button("🗑️ 清空画像", type="secondary"):
        repo.clear_profile(1)
        st.success("画像已清空")
        st.rerun()
