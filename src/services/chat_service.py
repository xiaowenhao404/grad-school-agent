"""ChatService — UI 与 LangGraph 之间的唯一入口。"""
from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any, Iterator


@lru_cache(maxsize=1)
def _get_graph():
    from src.graph.supervisor import build_supervisor_graph
    return build_supervisor_graph()


def _build_initial_state(user_id: int, conversation_id: int, user_input: str,
                         history: list, trace_sink: list | None = None,
                         saved_state: dict | None = None) -> dict:
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
    # 恢复跨轮 graph state（appointment_slots / metadata）
    if saved_state:
        if "appointment_slots" in saved_state:
            state["appointment_slots"] = saved_state["appointment_slots"]
        if "metadata" in saved_state:
            state["metadata"] = saved_state["metadata"]
    if trace_sink is not None:
        state["trace"] = trace_sink
    return state


def _persist_state(conversation_id: int, result_state: dict) -> None:
    """把 graph 跑完后的 appointment_slots / metadata 持久化。"""
    from src.db.repositories.conversation_state_repo import ConversationStateRepository
    try:
        ConversationStateRepository().save(
            conversation_id,
            appointment_slots=result_state.get("appointment_slots") or {},
            metadata=result_state.get("metadata") or {},
        )
    except Exception as e:
        # 持久化失败不应阻塞用户回复
        print(f"[chat_service] persist state failed: {e}")


class ChatService:
    def send_message(self, user_id: int, conversation_id: int | None,
                     user_input: str) -> dict[str, Any]:
        from src.db.repositories.conversation_repo import ConversationRepository
        from src.db.repositories.conversation_state_repo import ConversationStateRepository

        repo = ConversationRepository()
        if conversation_id is None:
            conversation_id = repo.start(user_id)

        history = repo.list_messages(conversation_id)
        saved_state = ConversationStateRepository().load(conversation_id)
        state = _build_initial_state(user_id, conversation_id, user_input, history,
                                     saved_state=saved_state)
        repo.add_message(conversation_id, "user", user_input)

        result = _get_graph().invoke(state)
        _persist_state(conversation_id, result)

        reply = result.get("agent_response", "")
        agent_name = ""
        for m in reversed(result.get("messages", [])):
            if m.get("role") == "assistant":
                agent_name = m.get("agent_name", "")
                break

        if reply:
            repo.add_message(conversation_id, "assistant", reply, agent_name=agent_name)

        return {
            "conversation_id": conversation_id,
            "agent_response": reply,
            "agent_name": agent_name,
            "task_type": result.get("task_type", ""),
            "trace": result.get("trace", []),
        }

    def stream_message(self, user_id: int, conversation_id: int | None,
                       user_input: str) -> Iterator[dict[str, Any]]:
        """边运行 graph 边推送 trace。

        每次 yield 一个事件 dict：
          - {"type": "init", "conversation_id": int}
          - {"type": "trace", "agent": str, "label": str, "text": str}
          - {"type": "final", "agent_response": str, "agent_name": str, "task_type": str}
        """
        from src.db.repositories.conversation_repo import ConversationRepository
        from src.db.repositories.conversation_state_repo import ConversationStateRepository

        repo = ConversationRepository()
        if conversation_id is None:
            conversation_id = repo.start(user_id)
        yield {"type": "init", "conversation_id": conversation_id}

        history = repo.list_messages(conversation_id)
        saved_state = ConversationStateRepository().load(conversation_id)
        # 共享 trace 列表：agent 在线程里 append，主线程定时拉取增量
        trace_sink: list = []
        state = _build_initial_state(user_id, conversation_id, user_input, history,
                                     trace_sink, saved_state=saved_state)
        repo.add_message(conversation_id, "user", user_input)

        result_holder: dict = {}
        error_holder: dict = {}

        def _run():
            try:
                result_holder["result"] = _get_graph().invoke(state)
            except Exception as e:
                import traceback
                traceback.print_exc()
                error_holder["error"] = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        sent = 0
        import time
        # 启动后立刻发一条 heartbeat，让浏览器尽快收到首个字节，建立连接
        yield {"type": "heartbeat", "ts": int(time.time())}
        last_heartbeat = time.time()
        while t.is_alive():
            while sent < len(trace_sink):
                yield {"type": "trace", **trace_sink[sent]}
                sent += 1
                last_heartbeat = time.time()
            # SSE 心跳：每 1 秒发一次，防止 LLM 调用阻塞导致浏览器超时
            now = time.time()
            if now - last_heartbeat >= 1.0:
                yield {"type": "heartbeat", "ts": int(now)}
                last_heartbeat = now
            time.sleep(0.05)
        # flush 剩余
        while sent < len(trace_sink):
            yield {"type": "trace", **trace_sink[sent]}
            sent += 1

        if error_holder:
            err = error_holder["error"]
            # 多 yield 一条 trace 把根因明文写到工作流链路里
            yield {"type": "trace", "agent": "system", "label": "系统",
                   "text": f"⚠️ 后端处理出错：{type(err).__name__}: {str(err)[:200]}"}
            time.sleep(0.05)
            yield {
                "type": "final",
                "agent_response": f"⚠️ 后端处理出错：{type(err).__name__}: {err}",
                "agent_name": "system",
                "task_type": "error",
            }
            return

        result = result_holder.get("result", {})
        # 持久化跨轮 graph state（appointment_slots / metadata）
        _persist_state(conversation_id, result)
        reply = result.get("agent_response", "")
        agent_name = ""
        for m in reversed(result.get("messages", [])):
            if m.get("role") == "assistant":
                agent_name = m.get("agent_name", "")
                break
        if reply:
            repo.add_message(conversation_id, "assistant", reply, agent_name=agent_name)

        yield {
            "type": "final",
            "agent_response": reply,
            "agent_name": agent_name,
            "task_type": result.get("task_type", ""),
        }

    def clear_conversation(self, user_id: int) -> None:
        from src.db.repositories.conversation_repo import ConversationRepository
        from src.db.repositories.user_repo import UserRepository
        # 先把该用户所有 conversation 的 state 也清掉（避免成孤儿）
        from src.db.engine import get_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text as _t
        with sessionmaker(bind=get_engine())() as s:
            s.execute(_t(
                "DELETE FROM conversation_state WHERE conversation_id IN "
                "(SELECT id FROM conversations WHERE user_id=:uid)"
            ), {"uid": user_id})
            s.commit()
        ConversationRepository().clear(user_id)
        UserRepository().clear_profile(user_id)
