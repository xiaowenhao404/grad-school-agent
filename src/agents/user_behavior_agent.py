"""UserBehaviorAgent — 用户行为分析机器人（方案 C）。

详见 DEV_SPEC.md 6.5 节。

承担三个角色：
1. pre-hook：对话前从 user_profile 注入画像到 state（受 memory_enabled 控制）
2. post-hook：对话后异步用 LLM 从本轮对话提取偏好，更新 user_profile
3. 显式入口：classifier 路由 task_type=='behavior' 时，渲染用户画像
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

Mode = Literal["extract", "display"]


class UserBehaviorAgent(BaseAgent):
    name = "user_behavior"
    prompt_file = "user_behavior.txt"

    def run(self, state: "GraphState") -> "GraphState":
        """显式入口：mode='display'，渲染用户画像。"""
        # TODO: 调用 self.display(state['user_profile']) 返回友好描述
        raise NotImplementedError

    # --- 供 hooks 调用的辅助方法 ---

    def extract_preferences(self, messages: list) -> dict:
        """post-hook 异步调用：从对话提取偏好 JSON。"""
        # TODO: mode='extract'，LLM 输出 JSON
        raise NotImplementedError

    def display(self, user_profile: dict) -> str:
        """显式入口：渲染画像为中文描述。"""
        # TODO: mode='display'，LLM 生成 3-5 句话描述
        raise NotImplementedError
