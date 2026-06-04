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
    label_zh = "归类机器人"
    prompt_file = "task_classifier.txt"

    _ROUTE_LABELS = {
        "consultant": "咨询机器人",
        "school": "选校机器人",
        "appointment": "预约机器人",
        "behavior": "行为分析机器人",
        "reject": "拒绝（与本系统无关）",
    }

    _STAGE_ZH = {
        "collect_preferences": "收集老师偏好",
        "show_candidates": "展示候选老师",
        "show_slots": "选择老师空闲时段",
        "confirm": "确认预约信息",
        "done": "提交预约",
    }

    def _build_stage_hint(self, state: "GraphState") -> str:
        """根据 appointment_slots 和 metadata.school_prefs 拼接简短的上下文提示，
        帮助 classifier 理解用户是否在某个 expert 的多轮流程中。"""
        hints = []
        slots = state.get("appointment_slots") or {}
        stage = slots.get("current_stage")
        if stage and stage != "collect_preferences":
            cands = slots.get("candidate_teachers") or []
            cand_names = "、".join((t.get("name") or "?") for t in cands[:3])
            hints.append(
                f"⚡当前用户正处于「预约老师」流程，阶段：{self._STAGE_ZH.get(stage, stage)}"
                + (f"，候选老师：{cand_names}" if cand_names else "")
                + "。若本轮输入是该流程的延续（如选序号 1/2/3、确认/否、选择具体时间），保持 appointment。"
            )
        meta = state.get("metadata") or {}
        sp = meta.get("school_prefs") or {}
        if sp:
            hints.append(
                f"⚡当前用户正在「选校」流程，已累积偏好键：{list(sp.keys())}。"
                "若本轮输入是补充选校字段（学费/语言/学制等），保持 school。"
            )
        if not hints:
            return "（无）"
        return "\n".join(hints)[:200]

    def run(self, state: "GraphState") -> "GraphState":
        user_input = state.get("user_input", "")
        self._trace(state, f"我收到您的输入：「{user_input[:60]}」，正在判断任务类型…")
        messages_str = "\n".join(
            f"{m['role']}: {m['content']}" for m in state.get("messages", [])[-6:]
        )
        stage_hint = self._build_stage_hint(state)
        prompt = self._render_prompt(
            user_profile=json.dumps(state.get("user_profile", {}), ensure_ascii=False),
            messages=messages_str,
            user_input=user_input,
            stage_hint=stage_hint,
        )
        llm = self._get_llm()
        try:
            resp = llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            self._trace(state, f"⚠️ LLM 调用失败：{type(e).__name__}: {str(e)[:100]}，默认路由 consultant。")
            state["task_type"] = "consultant"
            return state
        content = resp["content"].lower()
        task_type = "reject"
        for t in VALID_TASK_TYPES:
            if t in content:
                task_type = t
                break
        if task_type not in VALID_TASK_TYPES:
            task_type = "reject"
        state["task_type"] = task_type
        target = self._ROUTE_LABELS.get(task_type, task_type)
        if task_type == "reject":
            self._trace(state, "判定为：与申研、选校、预约、签证等服务无关，已拒绝。")
        else:
            self._trace(state, f"判定为「{task_type}」任务，转交「{target}」处理。")
        return state

