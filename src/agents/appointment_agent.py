"""AppointmentAgent — 预约机器人（含预约状态机）。

详见 DEV_SPEC.md 6.4 节、4.4.3 节预约状态机图。

实现：本 Agent 内部封装一个 LangGraph subgraph 状态机：
    collect_preferences -> show_candidates -> show_slots -> confirm -> done
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState


class AppointmentStage(str, Enum):
    COLLECT_PREFERENCES = "collect_preferences"
    SHOW_CANDIDATES = "show_candidates"
    SHOW_SLOTS = "show_slots"
    CONFIRM = "confirm"
    DONE = "done"


REQUIRED_TEACHER_PREFERENCES = (
    "gender",              # male/female/any
    "study_abroad",        # 是否要求有留学经历
    "expertise_regions",   # list[str]
    "expertise_majors",    # list[str]
)


class AppointmentAgent(BaseAgent):
    name = "appointment"
    prompt_file = "appointment.txt"

    def run(self, state: "GraphState") -> "GraphState":
        # TODO: 实现状态机
        # 1. 读 state['appointment_slots']['current_stage']（默认 COLLECT_PREFERENCES）
        # 2. 根据 stage 走对应分支：
        #    - COLLECT_PREFERENCES: 收集 REQUIRED_TEACHER_PREFERENCES
        #    - SHOW_CANDIDATES: HybridSearch(teachers) + TeacherRepository 获取候选
        #    - SHOW_SLOTS: TeacherScheduleRepository.list_available(teacher_id)
        #    - CONFIRM: 复述并等待"确认"
        #    - DONE: AppointmentRepository.create() + 更新 slot 状态
        # 3. 推进 stage 并写回 state
        raise NotImplementedError
