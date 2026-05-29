"""LangGraph pre/post hook 节点。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import GraphState


def pre_hook(state: "GraphState") -> "GraphState":
    if not state.get("memory_enabled", True):
        state["user_profile"] = {}
        return state
    from src.db.repositories.user_repo import UserRepository
    repo = UserRepository()
    profile = repo.get_profile(state.get("user_id", 1))
    state["user_profile"] = profile.get("preferences", {})
    state["memory_enabled"] = profile.get("memory_enabled", True)
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
