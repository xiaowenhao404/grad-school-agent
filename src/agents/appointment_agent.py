"""AppointmentAgent — 预约机器人（if/elif 状态机）。"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

REQUIRED_TEACHER_PREFS = ("gender", "expertise_regions", "expertise_majors")


class AppointmentAgent(BaseAgent):
    name = "appointment"
    prompt_file = "appointment.txt"

    def run(self, state: "GraphState") -> "GraphState":
        slots: dict = state.setdefault("appointment_slots", {})
        stage = slots.get("current_stage", "collect_preferences")

        if stage == "collect_preferences":
            return self._collect(state, slots)
        elif stage == "show_candidates":
            return self._show_candidates(state, slots)
        elif stage == "show_slots":
            return self._show_slots(state, slots)
        elif stage == "confirm":
            return self._confirm(state, slots)
        else:
            return self._done(state, slots)

    # ── stages ────────────────────────────────────────────────────────────────

    def _collect(self, state, slots):
        prefs: dict = slots.setdefault("collected_preferences", {})
        llm = self._get_llm()
        extract_prompt = (
            "从用户输入中提取预约老师偏好，输出 JSON（缺失用 null）：\n"
            '{"gender":"male/female/any","expertise_regions":"","expertise_majors":""}\n'
            f"用户输入：{state.get('user_input', '')}"
        )
        try:
            raw = llm.chat([{"role": "user", "content": extract_prompt}],
                           response_format={"type": "json_object"})
            new_p = json.loads(raw["content"])
            for k, v in new_p.items():
                if v and v != "null":
                    prefs[k] = v
        except Exception:
            pass

        missing = [k for k in REQUIRED_TEACHER_PREFS if not prefs.get(k)]
        if missing:
            ask = f"请告诉我您对老师的偏好：{', '.join(missing[:2])}（如性别、擅长地区、擅长专业）"
            state["agent_response"] = ask
            self._append_message(state, "assistant", ask)
            return state

        slots["current_stage"] = "show_candidates"
        return self._show_candidates(state, slots)

    def _show_candidates(self, state, slots):
        from src.db.engine import get_engine
        from src.db.repositories.teacher_repo import TeacherRepository
        from src.rag.collections import CollectionName
        from src.rag.retrieval.retriever_factory import get_retriever

        prefs = slots.get("collected_preferences", {})
        retriever = get_retriever(CollectionName.TEACHERS)
        query = f"{prefs.get('expertise_regions','')} {prefs.get('expertise_majors','')} 留学咨询老师"
        results = retriever.search(query, top_k_final=5)
        teacher_ids = [r.metadata.get("teacher_id") for r in results if r.metadata.get("teacher_id")]

        repo = TeacherRepository(engine=get_engine())
        candidates = []
        for tid in teacher_ids[:3]:
            t = repo.get(tid)
            if t:
                candidates.append(t)

        if not candidates:
            candidates = repo.search_by_preferences(prefs, limit=3)

        slots["candidate_teachers"] = candidates
        if not candidates:
            reply = "暂未找到符合条件的老师，请放宽条件后重试。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            slots["current_stage"] = "collect_preferences"
            return state

        lines = ["为您找到以下老师，请输入序号选择："]
        for i, t in enumerate(candidates, 1):
            lines.append(f"{i}. {t['name']}（{t['gender']}）— 擅长：{t.get('expertise_regions','')} / {t.get('expertise_majors','')}")
        reply = "\n".join(lines)
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        slots["current_stage"] = "show_slots"
        return state

    def _show_slots(self, state, slots):
        from src.db.engine import get_engine
        from src.db.repositories.teacher_repo import TeacherScheduleRepository

        user_input = state.get("user_input", "")
        candidates = slots.get("candidate_teachers", [])
        selected = None

        m = re.search(r"[1-3]", user_input)
        if m and candidates:
            idx = int(m.group()) - 1
            if 0 <= idx < len(candidates):
                selected = candidates[idx]

        if not selected and candidates:
            for t in candidates:
                if t["name"] in user_input:
                    selected = t
                    break

        if not selected:
            reply = "请输入序号（1/2/3）选择老师。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            return state

        slots["selected_teacher"] = selected
        repo = TeacherScheduleRepository(engine=get_engine())
        avail = repo.list_available(selected["id"], limit=5)
        slots["available_slots"] = avail

        if not avail:
            reply = f"{selected['name']} 近期暂无可用时间，请选择其他老师。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            slots["current_stage"] = "show_candidates"
            return state

        lines = [f"以下是 {selected['name']} 的可用时间，请输入序号选择："]
        for i, s in enumerate(avail, 1):
            lines.append(f"{i}. {s['date']} {s['time_slot']}")
        reply = "\n".join(lines)
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        slots["current_stage"] = "confirm"
        return state

    def _confirm(self, state, slots):
        user_input = state.get("user_input", "")
        avail = slots.get("available_slots", [])
        selected_slot = None

        m = re.search(r"[1-5]", user_input)
        if m and avail:
            idx = int(m.group()) - 1
            if 0 <= idx < len(avail):
                selected_slot = avail[idx]

        if not selected_slot:
            reply = "请输入序号选择时间段。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            return state

        slots["selected_slot"] = selected_slot
        teacher = slots.get("selected_teacher", {})
        reply = (
            f"确认预约信息：\n"
            f"- 老师：{teacher.get('name')}\n"
            f"- 时间：{selected_slot['date']} {selected_slot['time_slot']}\n"
            "请回复「确认」完成预约，或「重新选择」重来。"
        )
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        slots["current_stage"] = "done"
        return state

    def _done(self, state, slots):
        user_input = state.get("user_input", "").lower()
        if "重新" in user_input or "cancel" in user_input:
            slots.clear()
            reply = "已取消，请重新告诉我您的需求。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            return state

        from src.db.engine import get_engine
        from src.db.repositories.appointment_repo import AppointmentRepository

        teacher = slots.get("selected_teacher", {})
        slot = slots.get("selected_slot", {})
        try:
            repo = AppointmentRepository(engine=get_engine())
            appt_id = repo.create(
                user_id=state.get("user_id", 1),
                teacher_id=teacher["id"],
                schedule_id=slot["id"],
                topic=state.get("user_input", ""),
            )
            reply = f"预约成功！订单号：{appt_id}。{teacher.get('name')} 将在 {slot['date']} {slot['time_slot']} 与您联系。"
            slots.clear()
        except ValueError as e:
            reply = f"预约失败：{e}，请重新选择时间。"
            slots["current_stage"] = "show_slots"

        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state
