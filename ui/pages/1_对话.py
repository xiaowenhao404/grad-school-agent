"""页面 1：对话窗口。

详见 DEV_SPEC.md 4.1 节、第 6 章各 Agent。

功能：
- 用户输入框 + 历史消息展示
- 侧边栏：清空对话按钮、记忆开关 toggle
- 每条 assistant 消息显示由哪个 Agent 生成（小标签）
"""
from __future__ import annotations

# import streamlit as st
# from src.services.chat_service import ChatService


def render() -> None:
    # TODO:
    # st.title("💬 对话")
    # 侧边栏：
    #   memory_enabled = st.sidebar.toggle("记住我的偏好", value=...)
    #   if st.sidebar.button("清空对话"): ChatService.clear_conversation(user_id)
    # 主区：
    #   for msg in messages: st.chat_message(msg.role).markdown(msg.content + f" `via {msg.agent_name}`")
    #   user_input = st.chat_input("请输入...")
    #   if user_input: ChatService.handle(...) -> 追加消息并 rerun
    pass


render()
