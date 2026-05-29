"""ChatService — UI 与 LangGraph 之间的唯一入口。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _get_graph():
    from src.graph.supervisor import build_supervisor_graph
    return build_supervisor_graph()


class ChatService:
    def send_message(self, user_id: int, conversation_id: int | None,
                     user_input: str) -> dict[str, Any]:
        from src.db.engine import get_engine
        from src.db.repositories.conversation_repo import ConversationRepository

        repo = ConversationRepository()
        if conversation_id is None:
            conversation_id = repo.start(user_id)

        # 加载历史消息
        history = repo.list_messages(conversation_id)
        state = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "user_input": user_input,
            "user_profile": {},
            "memory_enabled": True,
            "messages": [
                {"role": m["role"], "agent_name": m.get("agent_name", ""),
                 "content": m["content"], "created_at": str(m.get("created_at", ""))}
                for m in history
            ],
        }

        # 持久化用户消息
        repo.add_message(conversation_id, "user", user_input)

        # 运行 graph
        result = _get_graph().invoke(state)

        reply = result.get("agent_response", "")
        agent_name = ""
        for m in reversed(result.get("messages", [])):
            if m.get("role") == "assistant":
                agent_name = m.get("agent_name", "")
                break

        # 持久化 assistant 消息
        if reply:
            repo.add_message(conversation_id, "assistant", reply, agent_name=agent_name)

        return {
            "conversation_id": conversation_id,
            "agent_response": reply,
            "agent_name": agent_name,
            "task_type": result.get("task_type", ""),
        }

    def clear_conversation(self, user_id: int) -> None:
        from src.db.engine import get_engine
        from src.db.repositories.conversation_repo import ConversationRepository
        from src.db.repositories.user_repo import UserRepository
        ConversationRepository(engine=get_engine()).clear(user_id)
        UserRepository(engine=get_engine()).clear_profile(user_id)
