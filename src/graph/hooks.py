"""LangGraph pre/post hook 节点。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import GraphState


# 显式打断词：命中后强制清空所有进行中的多轮流程状态
_BREAK_KEYWORDS = (
    "不约了", "算了", "换个话题", "换个问题", "取消预约",
    "重新开始", "返回主菜单", "退出", "不想约了", "不要预约了",
)


def _check_break(state: "GraphState") -> None:
    """检查用户输入是否包含"打断词"，命中则清空多轮流程状态。"""
    user_input = (state.get("user_input") or "").lower()
    if not any(kw in user_input for kw in _BREAK_KEYWORDS):
        return
    cleared = []
    if state.get("appointment_slots"):
        state["appointment_slots"] = {}
        cleared.append("预约流程")
    meta = state.get("metadata") or {}
    if meta.get("school_prefs"):
        meta["school_prefs"] = {}
        state["metadata"] = meta
        cleared.append("选校流程")
    if cleared:
        trace = state.setdefault("trace", [])
        trace.append({
            "agent": "system", "label": "系统",
            "text": f"✨ 已识别打断意图，清空：{'、'.join(cleared)}。重新为您分类本轮请求…",
        })


def pre_hook(state: "GraphState") -> "GraphState":
    # 1. 加载偏好画像
    if not state.get("memory_enabled", True):
        state["user_profile"] = {}
    else:
        from src.db.repositories.user_repo import UserRepository
        repo = UserRepository()
        profile = repo.get_profile(state.get("user_id", 1))
        state["user_profile"] = profile.get("preferences", {})
        state["memory_enabled"] = profile.get("memory_enabled", True)

    # 2. 检查是否有显式打断词
    _check_break(state)

    return state


def post_hook(state: "GraphState") -> "GraphState":
    if not state.get("memory_enabled", True):
        return state
    from src.agents.user_behavior_agent import UserBehaviorAgent
    from src.db.repositories.user_repo import UserRepository
    agent = UserBehaviorAgent()
    new_prefs = agent.extract_preferences(state.get("messages", []))
    if new_prefs:
        UserRepository().update_profile(state.get("user_id", 1), new_prefs)
    return state
