"""TaskClassifier — 任务分类机器人（入口路由）。

详见 DEV_SPEC.md 6.1 节。

职责：将用户输入分类为 consultant / school / appointment / behavior / reject，
结果写入 state['task_type']，由 supervisor 据此做 conditional edge 路由。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

TaskType = Literal["consultant", "school", "appointment", "behavior", "reject"]
VALID_TASK_TYPES: tuple[TaskType, ...] = (
    "consultant", "school", "appointment", "behavior", "reject",
)


class TaskClassifier(BaseAgent):
    name = "task_classifier"
    prompt_file = "task_classifier.txt"

    def run(self, state: "GraphState") -> "GraphState":
        # TODO: 实现 LLM 分类逻辑
        # 1. 加载 prompt_file 模板
        # 2. 渲染 user_profile / messages / user_input
        # 3. 调用 LLM
        # 4. 解析输出并校验是否在 VALID_TASK_TYPES 中
        # 5. 写入 state['task_type']
        raise NotImplementedError
