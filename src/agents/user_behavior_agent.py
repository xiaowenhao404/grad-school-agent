"""UserBehaviorAgent — 用户行为分析机器人（方案 C）。"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState


class UserBehaviorAgent(BaseAgent):
    name = "user_behavior"
    label_zh = "行为分析机器人"
    prompt_file = "user_behavior.txt"

    def run(self, state: "GraphState") -> "GraphState":
        """显式入口：渲染用户画像。"""
        profile = state.get("user_profile", {})
        self._trace(state, "正在读取您的历史偏好画像…")
        reply = self.display(profile)
        self._trace(state, "已生成画像总结。")
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state

    def extract_preferences(self, messages: list) -> dict:
        """post-hook 调用：从对话提取偏好 JSON。"""
        msgs_str = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-10:])
        prompt = self._render_prompt(messages=msgs_str, user_profile="{}", mode="extract")
        llm = self._get_llm()
        try:
            resp = llm.chat([{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"})
            return json.loads(resp["content"])
        except Exception:
            return {}

    def display(self, user_profile: dict) -> str:
        """渲染画像为中文描述。"""
        if not user_profile:
            return "暂无偏好记录，继续对话后系统将自动学习您的偏好。"
        prompt = self._render_prompt(messages="", user_profile=json.dumps(user_profile, ensure_ascii=False), mode="display")
        llm = self._get_llm()
        try:
            resp = llm.chat([{"role": "user", "content": prompt}])
            return resp["content"]
        except Exception:
            return f"您的偏好：{json.dumps(user_profile, ensure_ascii=False)}"
