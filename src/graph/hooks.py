"""LangGraph pre/post hook 节点。

详见 DEV_SPEC.md 4.4.2 节、6.5 节方案 C。

pre_hook: 在 classifier 之前，从 DB 读 user_profile 注入 state
post_hook: 在 expert agent 之后，异步用 LLM 提取偏好更新 user_profile
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import GraphState


def pre_hook(state: "GraphState") -> "GraphState":
    """对话前注入用户画像（受 memory_enabled 控制）。"""
    # TODO:
    # 1. 读 UserRepository.get_profile(user_id) -> {preferences, memory_enabled}
    # 2. if memory_enabled: state['user_profile'] = preferences
    #    else: state['user_profile'] = {}
    raise NotImplementedError


def post_hook(state: "GraphState") -> "GraphState":
    """对话后异步更新用户画像（受 memory_enabled 控制）。

    实现上可以同步走（简化）或丢到 threading/asyncio task（生产）。
    课程项目建议先同步实现，标注 TODO 为异步化预留点。
    """
    # TODO:
    # 1. 如果 memory_enabled=False -> 直接 return state
    # 2. UserBehaviorAgent.extract_preferences(messages) -> new_prefs
    # 3. merge new_prefs into existing user_profile（去重/合并关键词列表）
    # 4. UserRepository.update_profile(user_id, merged)
    raise NotImplementedError
