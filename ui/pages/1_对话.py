"""页面 1：对话窗口。"""
import streamlit as st

st.set_page_config(page_title="对话", page_icon="💬", layout="wide")

# ── 初始化 session state ──────────────────────────────────────────────────────
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── 侧边栏 ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("设置")
    memory_on = st.toggle("记住我的偏好", value=True, key="memory_toggle")

    if st.button("🗑️ 清空对话", use_container_width=True):
        from src.services.chat_service import ChatService
        ChatService().clear_conversation(1)
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    if not memory_on:
        from src.db.engine import get_engine
        from src.db.repositories.user_repo import UserRepository
        UserRepository(engine=get_engine()).set_memory_enabled(1, False)
    else:
        from src.db.engine import get_engine
        from src.db.repositories.user_repo import UserRepository
        UserRepository(engine=get_engine()).set_memory_enabled(1, True)

# ── 主区：历史消息 ─────────────────────────────────────────────────────────────
st.title("💬 对话")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("agent_name"):
            st.caption(f"via {msg['agent_name']}")

# ── 输入框 ────────────────────────────────────────────────────────────────────
if user_input := st.chat_input("请输入您的问题..."):
    st.session_state.messages.append({"role": "user", "content": user_input, "agent_name": ""})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            from src.services.chat_service import ChatService
            result = ChatService().send_message(1, st.session_state.conversation_id, user_input)
            st.session_state.conversation_id = result["conversation_id"]
            reply = result["agent_response"]
            agent_name = result.get("agent_name", "")
        st.markdown(reply)
        if agent_name:
            st.caption(f"via {agent_name}")

    st.session_state.messages.append({"role": "assistant", "content": reply, "agent_name": agent_name})
