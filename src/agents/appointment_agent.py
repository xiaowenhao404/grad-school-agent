"""AppointmentAgent — 预约机器人（多轮偏好持久化 + 宽松校验）。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

TEACHER_FIELD_LABELS = {
    "gender": "老师性别",
    "expertise_regions": "擅长国家和地区",
    "expertise_majors": "擅长专业方向",
}


def _parse_slot_start(slot: dict) -> datetime | None:
    """slot 例：{'date':'2026-06-15','time_slot':'14:00-15:00'} → 2026-06-15 14:00"""
    try:
        date = slot.get("date", "")
        ts = (slot.get("time_slot") or "").split("-")[0].strip()
        return datetime.strptime(f"{date} {ts}", "%Y-%m-%d %H:%M")
    except Exception:
        return None


def _pick_closest_slot(slots: list[dict], wanted: str) -> dict | None:
    """从 available slots 中选与 wanted (YYYY-MM-DD HH:MM) 时间最接近的一个。"""
    try:
        # 兼容 ISO 与"YYYY-MM-DD HH:MM"两种格式
        if "T" in wanted:
            target = datetime.fromisoformat(wanted.replace("Z", ""))
        else:
            target = datetime.strptime(wanted.strip()[:16], "%Y-%m-%d %H:%M")
    except Exception:
        return None
    candidates = [(s, _parse_slot_start(s)) for s in slots]
    candidates = [(s, d) for s, d in candidates if d is not None]
    if not candidates:
        return None
    candidates.sort(key=lambda x: abs((x[1] - target).total_seconds()))
    return candidates[0][0]


class AppointmentAgent(BaseAgent):
    name = "appointment"
    label_zh = "预约机器人"
    prompt_file = "appointment.txt"

    def run(self, state: "GraphState") -> "GraphState":
        slots: dict = state.setdefault("appointment_slots", {})
        stage = slots.get("current_stage", "collect_preferences")
        stage_zh = {
            "collect_preferences": "收集老师偏好",
            "show_candidates": "展示候选老师",
            "show_slots": "展示空闲时间",
            "confirm": "确认预约信息",
            "done": "提交预约",
        }.get(stage, stage)
        self._trace(state, f"当前阶段：{stage_zh}")

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
        from src.db.repositories.user_repo import UserRepository

        # 跨轮持久化：从 user_profile.teacher_prefs 读取
        profile_prefs = (state.get("user_profile") or {}).get("teacher_prefs", {}) or {}
        prefs: dict = slots.setdefault("collected_preferences", dict(profile_prefs))

        extract_prompt = (
            "从【本轮用户输入】提取预约老师偏好，只输出 JSON（未提及字段置 null）：\n"
            '{"teacher_name":"","gender":"male/female/any/null","expertise_regions":"国家或地区","expertise_majors":"专业方向","start_time":"YYYY-MM-DD HH:MM 或 null","duration_min":30/60/90/120 或 null}\n'
            "解析规则：\n"
            "- **指定老师**：用户提到具体老师名字（如『张伟』『李明辉』『约张老师』），写入 teacher_name\n"
            "- 『男老师』⇒ male；『女老师』⇒ female；未指定 ⇒ null（不要瞎写 any）\n"
            "- 『美国留学』『英国申请』⇒ expertise_regions 写国家中文\n"
            "- CS/AI/计算机/商科/金融 ⇒ expertise_majors\n"
            "- **预约时间**：『明天下午 3 点』/『6 月 15 日 14:00』/『下周三上午十点』⇒ start_time 写 ISO 格式 YYYY-MM-DD HH:MM。今天日期作为参考基准：" + str(__import__('datetime').date.today()) + "\n"
            "- **时长**：『1 小时』⇒ 60；『半小时』⇒ 30；『两小时』⇒ 120；未指定 ⇒ null（系统会默认 60）\n"
            f"\n【本轮用户输入】{state.get('user_input','')}"
        )
        raw = self._safe_llm_chat(state, [{"role": "user", "content": extract_prompt}],
                                  response_format={"type": "json_object"})
        if raw:
            new_p = self._extract_json(raw["content"])
            for k, v in new_p.items():
                if v and v != "null" and v is not None:
                    prefs[k] = v

        # 持久化（teacher_name 是临时字段，不入持久化偏好）
        if state.get("memory_enabled", True):
            try:
                persist = {k: v for k, v in prefs.items() if k != "teacher_name"}
                if persist:
                    UserRepository().update_profile(state.get("user_id", 1), {"teacher_prefs": persist})
            except Exception:
                pass

        zh = "、".join(
            f"{TEACHER_FIELD_LABELS.get(k, k)}={v}"
            for k, v in prefs.items() if v and v != "null" and k != "teacher_name"
        )
        if zh:
            self._trace(state, f"已累积偏好：{zh}")

        # specific_name 直达：指定老师后跳过候选筛选，直接进入时段选择
        if prefs.get("teacher_name"):
            from src.db.repositories.teacher_repo import TeacherRepository as _TR
            tname = prefs["teacher_name"]
            self._trace(state, f"识别到具体老师名「{tname}」，直接精确匹配…")
            hits = _TR().search_by_name(tname, limit=3)
            if hits:
                slots["selected_teacher"] = hits[0]
                slots["candidate_teachers"] = hits[:1]
                self._trace(state, f"匹配到：{hits[0]['name']}，准备查询其空闲时段…")
                slots["current_stage"] = "show_slots"
                # 直接走 show_slots 流程；构造一个"序号 1"虚拟输入，让 _show_slots 直接锁定 selected
                state["user_input"] = "1"
                return self._show_slots(state, slots)
            else:
                self._trace(state, f"未找到名为「{tname}」的老师，回退到偏好匹配。")

        # ── 宽松校验：任意一条非空即可直接进入候选展示
        has_any = any(prefs.get(k) and prefs.get(k) != "null"
                      for k in ("gender", "expertise_regions", "expertise_majors"))
        if not has_any:
            ask = (
                "请告诉我您对老师的任意一项偏好：\n"
                "- 老师性别（男/女）\n"
                "- 擅长国家和地区（如：美国、英国、香港）\n"
                "- 擅长专业方向（如：CS、商科）\n\n"
                "💡 任选一项即可开始匹配，我会记住每一次补充。"
            )
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
        self._trace(state, "正在向量库中按擅长领域语义检索老师…")
        retriever = get_retriever(CollectionName.TEACHERS)
        query = " ".join(filter(None, [
            prefs.get("expertise_regions",""),
            prefs.get("expertise_majors",""),
            "留学咨询老师",
        ]))
        try:
            results = retriever.search(query, top_k_final=5)
        except Exception as e:
            self._trace(state, f"⚠️ 向量检索失败，将直接走数据库匹配：{type(e).__name__}")
            results = []
        teacher_ids = [r.metadata.get("teacher_id") for r in results if r.metadata.get("teacher_id")]

        repo = TeacherRepository(engine=get_engine())
        candidates = []
        for tid in teacher_ids[:3]:
            t = repo.get(tid)
            if t:
                candidates.append(t)

        if not candidates:
            self._trace(state, "向量召回为空，回退到关系数据库按偏好筛选…")
            candidates = repo.search_by_preferences(prefs, limit=3)

        # 最后兜底：还是空的话，放宽到任意 3 位老师
        if not candidates:
            self._trace(state, "条件过严，已放宽为推荐评分最高的 3 位老师。")
            all_t = repo.list_all()
            all_t.sort(key=lambda t: t.get("rating") or 0, reverse=True)
            candidates = all_t[:3]

        slots["candidate_teachers"] = candidates
        if not candidates:
            reply = "暂未找到任何老师，请稍后重试。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            slots["current_stage"] = "collect_preferences"
            return state

        self._trace(state, f"匹配到 {len(candidates)} 位候选老师：{'、'.join(t['name'] for t in candidates)}")
        lines = ["为您找到以下老师，请输入序号选择：\n"]
        for i, t in enumerate(candidates, 1):
            emoji = '👨' if t['gender'] == 'male' else ('👩' if t['gender'] == 'female' else '🧑')
            bio = (t.get('bio') or '').strip()
            bio_short = (bio[:80] + '…') if len(bio) > 80 else bio
            lines.append(
                f"**{i}. {emoji} {t['name']}** ⭐ {t.get('rating', '—')}\n"
                + (f"> {bio_short}\n" if bio_short else "")
                + f"- 擅长：{t.get('expertise_regions','—')} / {t.get('expertise_majors','—')}\n"
                + f"- [📖 查看完整简介](#teacher-{t['id']})"
            )
        reply = "\n\n".join(lines)
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
        self._trace(state, f"用户已选择 {selected['name']} 老师，正在查询其空闲时段…")
        repo = TeacherScheduleRepository(engine=get_engine())
        avail = repo.list_available(selected["id"], limit=5)
        slots["available_slots"] = avail

        if not avail:
            self._trace(state, f"{selected['name']} 近期无空闲时段。")
            reply = f"{selected['name']} 近期暂无可用时间，请选择其他老师。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            slots["current_stage"] = "show_candidates"
            return state

        self._trace(state, f"找到 {len(avail)} 个可预约时段。")

        # 如果用户已指定 start_time，自动定位最接近的时段，跳过手动选号
        prefs = slots.get("collected_preferences", {})
        wanted_start = (prefs.get("start_time") or "").strip()
        if wanted_start:
            best = _pick_closest_slot(avail, wanted_start)
            if best:
                slots["selected_slot"] = best
                duration = prefs.get("duration_min") or 60
                self._trace(state, f"已为您匹配最接近时段：{best['date']} {best['time_slot']}（时长 {duration} 分钟）")
                reply = (
                    f"确认预约信息：\n"
                    f"- 老师：{selected.get('name')}\n"
                    f"- 时间：{best['date']} {best['time_slot']}\n"
                    f"- 时长：{duration} 分钟\n"
                    "请回复「确认」完成预约，或「重新选择」重来。"
                )
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                slots["current_stage"] = "done"
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
        prefs = slots.get("collected_preferences", {})
        duration = prefs.get("duration_min") or 60
        try:
            self._trace(state, f"正在写入数据库：{teacher.get('name')} @ {slot.get('date')} {slot.get('time_slot')}（时长 {duration} 分钟）")
            repo = AppointmentRepository(engine=get_engine())
            # 把时长拼进 topic 字段，避免改 schema 也能保留信息
            topic = state.get("user_input", "")
            topic_with_dur = (topic + f" [时长: {duration}min]").strip()
            appt_id = repo.create(
                user_id=state.get("user_id", 1),
                teacher_id=teacher["id"],
                schedule_id=slot["id"],
                topic=topic_with_dur,
            )
            self._trace(state, f"预约成功，订单号 #{appt_id}，时段已置为已预订。")
            reply = (
                f"✅ **预约成功！** 订单号：#{appt_id}\n\n"
                f"- 👨‍🏫 老师：{teacher.get('name')}\n"
                f"- 🕐 时间：{slot['date']} {slot['time_slot']}\n"
                f"- ⏱️ 时长：{duration} 分钟\n\n"
                f"{teacher.get('name')} 将届时与您联系，请保持手机畅通。"
            )
            slots.clear()
        except ValueError as e:
            self._trace(state, f"预约失败：{e}")
            reply = f"预约失败：{e}，请重新选择时间。"
            slots["current_stage"] = "show_slots"

        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state
