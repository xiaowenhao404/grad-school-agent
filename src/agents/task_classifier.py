"""TaskClassifier — 任务分类机器人（入口路由）。"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

TaskType = Literal["consultant", "school", "appointment", "behavior", "reject"]
VALID_TASK_TYPES: tuple[str, ...] = ("consultant", "school", "appointment", "behavior", "reject")


class TaskClassifier(BaseAgent):
    name = "task_classifier"
    prompt_file = "task_classifier.txt"

    def run(self, state: "GraphState") -> "GraphState":
        messages_str = "\n".join(
            f"{m['role']}: {m['content']}" for m in state.get("messages", [])[-6:]
        )
        prompt = self._render_prompt(
            user_profile=json.dumps(state.get("user_profile", {}), ensure_ascii=False),
            messages=messages_str,
            user_input=state.get("user_input", ""),
        )
        llm = self._get_llm()
        resp = llm.chat([{"role": "user", "content": prompt}])
        content = resp["content"].lower()
        import re
        task_type = "reject"
        for t in VALID_TASK_TYPES:
            if t in content:
                task_type = t
                break
        if task_type not in VALID_TASK_TYPES:
            task_type = "reject"
        state["task_type"] = task_type
        return state

