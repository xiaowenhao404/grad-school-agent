"""LangGraph 状态定义。

详见 DEV_SPEC.md 4.4.1 节。
"""
from __future__ import annotations

from typing import Any, TypedDict


class Message(TypedDict):
    role: str             # 'user' | 'assistant' | 'system'
    agent_name: str       # 哪个 agent 产生（user 消息为空字符串）
    content: str
    created_at: str


class AppointmentSlots(TypedDict, total=False):
    """预约状态机专用字段。"""
    current_stage: str                 # AppointmentStage enum value
    collected_preferences: dict
    candidate_teachers: list[dict]
    selected_teacher: dict | None
    available_slots: list[dict]
    selected_slot: dict | None
    appointment_id: int | None         # 创建成功后填入


class GraphState(TypedDict, total=False):
    """LangGraph 在 node 间传递的状态。"""
    # 身份
    user_id: int
    conversation_id: int

    # 本轮输入
    user_input: str

    # pre-hook 注入
    user_profile: dict
    memory_enabled: bool

    # classifier 输出
    task_type: str                     # consultant/school/appointment/behavior/reject

    # 对话历史（会话内）
    messages: list[Message]

    # 当前 agent 回复
    agent_response: str

    # 元数据
    metadata: dict[str, Any]

    # 预约状态机
    appointment_slots: AppointmentSlots

    # 工作流可视化追踪（前端展示思考过程）
    # 每项形如 {"agent": "task_classifier", "label": "归类机器人", "text": "..."}
    trace: list[dict]
