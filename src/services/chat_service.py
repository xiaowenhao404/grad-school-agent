"""ChatService — UI 与 LangGraph 之间的入口。

UI 把用户输入交给 ChatService.handle()，由其包装为 GraphState 并触发 supervisor。
"""
from __future__ import annotations

from typing import Any


class ChatService:
    def __init__(self):
        # TODO: build_supervisor_graph() 缓存编译后的 graph
        self._graph = None

    def handle(self, user_id: int, conversation_id: int, user_input: str) -> dict[str, Any]:
        """处理一轮对话。

        Returns:
            {agent_response: str, agent_name: str, task_type: str, ...}
        """
        # TODO:
        # 1. 构造 GraphState（含 messages 历史）
        # 2. self._graph.invoke(state)
        # 3. 返回展示所需字段
        raise NotImplementedError

    def clear_conversation(self, user_id: int) -> None:
        """清空对话 + 用户画像（受 memory_enabled 约束，但清空时强制清除）。"""
        # TODO: ConversationRepository.clear + UserRepository.clear_profile
        raise NotImplementedError
