"""SchoolSelectionAgent — 选校机器人。

详见 DEV_SPEC.md 6.3 节。

职责：多轮收集结构化偏好 -> 两段式检索（SQL 过滤 + Chroma 语义检索） -> 返回项目卡片。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState


REQUIRED_PREFERENCE_FIELDS = (
    "tuition_range",      # [min, max] USD/年
    "qs_rank_range",      # [min, max]
    "country",            # str
    "major_category",     # str
    "duration_max",       # int months
    "language_score",     # {"ielts": float} or {"toefl": float}
)


class SchoolSelectionAgent(BaseAgent):
    name = "school_selection"
    prompt_file = "school_selection.txt"

    def run(self, state: "GraphState") -> "GraphState":
        # TODO:
        # 1. 从 state 读取/更新 collected_preferences
        # 2. 检查 REQUIRED_PREFERENCE_FIELDS 是否齐全
        #    - 不齐：渲染追问 prompt 调 LLM 返回
        #    - 齐全：进入两段式检索
        # 3. 两段式检索：
        #    a) SchoolRepository.filter_programs(preferences) -> program_ids
        #    b) HybridSearch(schools collection, where program_id IN program_ids)
        # 4. 用项目卡片格式渲染 Top3 结果
        raise NotImplementedError
