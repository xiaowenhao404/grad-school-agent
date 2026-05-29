"""Streamlit 入口 — 默认重定向到对话页面。

启动命令：`uv run streamlit run app.py`

Streamlit 自动从 `pages/` 目录加载多页面（命名 `1_...py`, `2_...py` 决定侧边栏顺序）。
本文件作为主入口仅显示欢迎信息与导航说明。
"""
from __future__ import annotations

# import streamlit as st


def main() -> None:
    # TODO: 改为真实 Streamlit 调用
    # st.set_page_config(page_title="申研选校助手", page_icon="🎓", layout="wide")
    # st.title("🎓 申研选校助手")
    # st.markdown("从左侧侧边栏选择功能页面。")
    # st.info(
    #     "💡 提示：首次使用请先到『知识库管理』导入资料，"
    #     "或运行 `uv run python -m src.db.init_db` 导入 seed 数据。"
    # )
    print("[app.py] 占位 — 见 DEV_SPEC.md 第 3.5 节 Streamlit 前端")


if __name__ == "__main__":
    main()
