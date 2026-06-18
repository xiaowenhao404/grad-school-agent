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
            "confirm": "选择时段",
            "ask_mode": "线上/线下 + 联系方式",
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
        elif stage == "ask_mode":
            return self._ask_mode(state, slots)
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
            "- **预约时间（重要！）**：用户提到任何日期表达（『6月5日』『明天』『下周三』『2026-06-05』）⇒ start_time 必须写 ISO 格式 YYYY-MM-DD HH:MM；如果只有日期没具体小时，HH:MM 部分用 00:00。今天日期作为参考基准：" + str(__import__('datetime').date.today()) + "\n"
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
                self._trace(state, f"❗ 未找到名为「{tname}」的老师，将回退到偏好匹配。")
                # 记下"未命中"以便 _show_candidates 在回复开头温柔说明
                slots["_missed_specific_name"] = tname
                # 清掉这个临时字段，避免下次 turn 还把它当指定老师
                prefs.pop("teacher_name", None)

        # ── 个性化兜底：若本轮没给任何偏好，用 user_profile.teacher_prefs 补
        profile_teacher = (state.get("user_profile") or {}).get("teacher_prefs", {}) or {}
        injected_from_profile = []
        for k in ("gender", "expertise_regions", "expertise_majors"):
            if not prefs.get(k) and profile_teacher.get(k):
                prefs[k] = profile_teacher[k]
                injected_from_profile.append(f"{TEACHER_FIELD_LABELS.get(k, k)}={profile_teacher[k]}")
        if injected_from_profile:
            self._trace(state, f"📊 行为分析机器人注入了您的历史偏好：{'、'.join(injected_from_profile)}")

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

        # 温柔提示：之前指定的老师没找到
        header_lines = []
        miss = slots.pop("_missed_specific_name", None)
        if miss:
            header_lines.append(f"😶 抱歉，未能为您找到名为「**{miss}**」的老师。")
            header_lines.append("根据您当前的偏好，为您推荐以下几位：\n")
        elif (state.get("user_profile") or {}).get("teacher_prefs"):
            # 行为分析有历史偏好被使用过
            header_lines.append("📊 已结合您的历史偏好进行个性化推荐：\n")
        else:
            header_lines.append("为您找到以下老师，请输入序号选择：\n")

        lines = header_lines
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

        # ── 用户已指定日期/时间：按日期过滤，命中则进 confirm，未命中则明确告知 + 提供其他时段 + 换老师选项
        prefs = slots.get("collected_preferences", {})
        wanted_start = (prefs.get("start_time") or "").strip()
        wanted_date = wanted_start[:10] if len(wanted_start) >= 10 else ""

        if wanted_date:
            all_av = repo.list_available(selected["id"], limit=999)
            on_date = [s for s in all_av if s["date"] == wanted_date]
            # 区分"只给日期"与"给了具体钟点"：LLM 对纯日期填占位 00:00
            wanted_time = wanted_start[11:16] if len(wanted_start) >= 16 else ""
            has_specific_hour = bool(wanted_time) and wanted_time != "00:00"
            if on_date:
                self._trace(state, f"{selected['name']} 在 {wanted_date} 有 {len(on_date)} 个空闲时段。")
                # 既指定日期又指定具体小时 → 自动 closest match → 进 ask_mode
                if has_specific_hour:
                    best = _pick_closest_slot(on_date, wanted_start)
                    if best:
                        slots["selected_slot"] = best
                        slots["available_slots"] = on_date
                        duration = prefs.get("duration_min") or 60
                        self._trace(state, f"已为您匹配最接近时段：{best['date']} {best['time_slot']}（时长 {duration} 分钟）")
                        slots["current_stage"] = "ask_mode"
                        return self._ask_mode(state, slots, first_round=True)
                # 仅指定日期 → 列出当日所有时段
                slots["available_slots"] = on_date
                lines = [f"{selected['name']} 老师在 **{wanted_date}** 的可用时段，请输入序号选择："]
                for i, s in enumerate(on_date, 1):
                    lines.append(f"{i}. {s['date']} {s['time_slot']}")
                reply = "\n".join(lines)
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                slots["current_stage"] = "confirm"
                return state
            else:
                # 该老师该日无空 → 明确告知 + 列出最近的其他时段 + 提供「换老师」选项
                other = all_av[:5]
                slots["available_slots"] = other
                prefs.pop("start_time", None)  # 已告知不可用，下一轮无需再匹配
                self._trace(state, f"❗ {selected['name']} 在 {wanted_date} 无空闲，已列出最近 {len(other)} 个其他时段。")
                lines = [
                    f"😶 抱歉，**{selected['name']}** 老师在 **{wanted_date}** 没有空闲时段。",
                    "",
                    "您可以：",
                    f"- 从 {selected['name']} 的其他空闲时段中选一个（输入序号）：",
                ]
                for i, s in enumerate(other, 1):
                    lines.append(f"  {i}. {s['date']} {s['time_slot']}")
                lines.append("")
                lines.append("- 或回复「**换老师**」让我重新推荐其他老师。")
                reply = "\n".join(lines)
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                slots["current_stage"] = "confirm"
                return state

        # ── 默认分支：用户未指定日期，取前 5 个
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

        # 用户主动要求换老师 → 回到 show_candidates，让 _show_candidates 重新挑
        if re.search(r"换老师|换个老师|其他老师|别的老师", user_input):
            self._trace(state, "用户要求换老师，返回候选列表。")
            # 清掉当前选择，保留 collected_preferences
            slots.pop("selected_teacher", None)
            slots.pop("available_slots", None)
            slots["current_stage"] = "show_candidates"
            return self._show_candidates(state, slots)

        m = re.search(r"[1-5]", user_input)
        if m and avail:
            idx = int(m.group()) - 1
            if 0 <= idx < len(avail):
                selected_slot = avail[idx]

        if not selected_slot:
            reply = "请输入序号选择时间段，或回复「**换老师**」让我重新推荐。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            return state

        slots["selected_slot"] = selected_slot
        # 进入 ask_mode：先问线上/线下，再问联系方式
        slots["current_stage"] = "ask_mode"
        return self._ask_mode(state, slots, first_round=True)

    def _ask_mode(self, state, slots, first_round: bool = False):
        """收集 meeting_mode (online/offline) + contact (phone/wechat)。

        Why: 线上约见需要电话/微信联系；线下需要给地点 + 当地天气提醒。
        """
        teacher = slots.get("selected_teacher", {})
        selected_slot = slots.get("selected_slot", {})
        mode = slots.get("meeting_mode")  # 'online' or 'offline'
        contact = slots.get("contact")
        user_input = state.get("user_input", "").strip()

        # 步骤 1：先问 mode
        if not mode:
            if first_round:
                reply = (
                    f"已为您锁定 **{teacher.get('name')}** 老师，时间 **{selected_slot['date']} {selected_slot['time_slot']}**。\n\n"
                    "请问您倾向：\n"
                    "- **1️⃣ 线上**（视频/电话沟通，需提供联系方式）\n"
                    "- **2️⃣ 线下**（到公司面谈，将提供当日天气提示）"
                )
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                return state
            # 解析用户回答
            inp = user_input.lower()
            mode_just_set = False
            if "1" in inp or "线上" in inp or "online" in inp or "视频" in inp or "电话" in inp:
                slots["meeting_mode"] = "online"
                mode = "online"
                mode_just_set = True
                self._trace(state, "用户选择：线上沟通")
            elif "2" in inp or "线下" in inp or "offline" in inp or "面谈" in inp or "到店" in inp:
                slots["meeting_mode"] = "offline"
                mode = "offline"
                mode_just_set = True
                self._trace(state, "用户选择：线下面谈")
            else:
                reply = "请回复 **1**（线上）或 **2**（线下）。"
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                return state
            # 刚识别到 mode=online → 先尝试从同一句里提取联系方式（避免逼用户重复输入）
            if mode == "online":
                phone_m = re.search(r"1\d{10}", user_input)
                wechat_m = re.search(r"(?:微信|vx|wx)[:：\s]*([A-Za-z0-9_-]{4,})", user_input)
                if phone_m:
                    slots["contact"] = phone_m.group()
                    self._trace(state, f"已从同句中识别联系方式：{phone_m.group()[:3]}****{phone_m.group()[-4:]}（电话）")
                    slots["current_stage"] = "done"
                    state["user_input"] = "确认"
                    return self._done(state, slots)
                if wechat_m:
                    slots["contact"] = "微信: " + wechat_m.group(1)
                    self._trace(state, f"已从同句中识别联系方式：微信 {wechat_m.group(1)}")
                    slots["current_stage"] = "done"
                    state["user_input"] = "确认"
                    return self._done(state, slots)
                # 没附带联系方式 → 下一轮请求
                reply = (
                    "好的，已选择 **线上沟通**。\n\n"
                    "请提供您的**联系方式**（11 位手机号 或 微信号），老师将通过此方式与您联系。"
                )
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                return state
            # mode=offline：不需要 contact，直接走到 done（下面的逻辑）
            _ = mode_just_set  # silence linter

        # 步骤 2：线上 → 必须问联系方式
        if mode == "online" and not contact:
            # 如果本轮输入像是联系方式，直接收下
            if first_round or not user_input:
                reply = "请提供您的**联系方式**（手机号或微信号），老师将通过此方式电话联系您。"
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                return state
            # 简单识别：含 11 位数字 / "微信" / "vx" / "wx"
            phone_m = re.search(r"1\d{10}", user_input)
            wechat_m = re.search(r"(?:微信|vx|wx)[:：\s]*([A-Za-z0-9_-]{4,})", user_input)
            if phone_m:
                slots["contact"] = phone_m.group()
                self._trace(state, f"已记录联系方式：{phone_m.group()[:3]}****{phone_m.group()[-4:]}（电话）")
            elif wechat_m:
                slots["contact"] = "微信: " + wechat_m.group(1)
                self._trace(state, f"已记录联系方式：微信 {wechat_m.group(1)}")
            elif len(user_input) >= 4:
                slots["contact"] = user_input[:50]
                self._trace(state, "已记录联系方式")
            else:
                reply = "联系方式格式无效，请提供 11 位手机号或微信号。"
                state["agent_response"] = reply
                self._append_message(state, "assistant", reply)
                return state

        # 步骤 3：信息齐全 → 进入 done，由 _done 调天气工具并写库
        slots["current_stage"] = "done"
        # 用一个"确认"虚拟输入触发 _done
        state["user_input"] = "确认"
        return self._done(state, slots)

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
        mode = slots.get("meeting_mode") or "online"
        contact = slots.get("contact") or ""
        mode_zh = "线上" if mode == "online" else "线下"

        try:
            self._trace(state, f"正在写入数据库：{teacher.get('name')} @ {slot.get('date')} {slot.get('time_slot')}（{mode_zh}，时长 {duration} 分钟）")
            repo = AppointmentRepository(engine=get_engine())
            # 把时长 + 模式 + 联系方式拼进 topic
            topic = state.get("user_input", "")
            topic_with_dur = (topic + f" [时长:{duration}min|{mode_zh}|{contact}]").strip()
            appt_id = repo.create(
                user_id=state.get("user_id", 1),
                teacher_id=teacher["id"],
                schedule_id=slot["id"],
                topic=topic_with_dur,
            )
            self._trace(state, f"预约成功，订单号 #{appt_id}，时段已置为已预订。")

            # 个性化回复：线上 → 提醒联系；线下 → 调天气工具
            extra_lines = []
            if mode == "online":
                extra_lines.append(f"- ☎️ 联系方式：{contact}")
                extra_lines.append(f"\n💬 **{teacher.get('name')}** 老师将在该时段通过您提供的联系方式与您沟通，请保持畅通。")
            else:
                # 线下：调天气工具
                extra_lines.append("- 📍 地点：到访我司线下咨询室")
                weather_line = self._fetch_weather_line(state, slot.get("date"))
                if weather_line:
                    extra_lines.append(weather_line)
                extra_lines.append(f"\n💬 请提前 10 分钟到达，**{teacher.get('name')}** 老师将在咨询室等候。")

            reply = (
                f"✅ **预约成功！** 订单号：#{appt_id}\n\n"
                f"- 👨‍🏫 老师：{teacher.get('name')}\n"
                f"- 🕐 时间：{slot['date']} {slot['time_slot']}\n"
                f"- ⏱️ 时长：{duration} 分钟\n"
                f"- 💼 形式：{mode_zh}\n"
                + "\n".join(extra_lines)
                + f"\n\n📅 已写入数据库，可前往 [时间表](/schedule?date={slot['date']}) 查看该时段状态变化。"
            )
            slots.clear()
        except ValueError as e:
            self._trace(state, f"预约失败：{e}")
            reply = f"预约失败：{e}，请重新选择时间。"
            slots["current_stage"] = "show_slots"

        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state

    def _fetch_weather_line(self, state, date_str: str | None) -> str:
        """对线下预约，通过 MCP-like tool registry 查公司所在地（上海）当日天气，给个性化提示。"""
        from src.tools.registry import registry
        try:
            self._trace(state, "🌤️ 通过 MCP-like 协议调用 weather_query 工具…")
            w = registry.call_tool(
                "weather_query",
                _trace_cb=lambda txt: self._trace(state, txt),
                city="Shanghai",
            )
        except Exception as e:
            self._trace(state, f"⚠️ 天气查询失败：{type(e).__name__}")
            return ""
        if w.get("source") == "unavailable":
            return ""
        cond = w.get("condition", "")
        temp = w.get("temp_c")
        tip = ""
        c = cond.lower() if isinstance(cond, str) else ""
        if "雨" in cond or "rain" in c or "shower" in c:
            tip = "建议携带雨具 ☔"
        elif temp is not None and temp >= 30:
            tip = "天气炎热，请注意防暑 ☀️"
        elif temp is not None and temp <= 10:
            tip = "气温较低，请注意保暖 🧥"
        return f"- 🌤️ {date_str or '当日'}上海天气：{cond}，{temp}°C{'，' + tip if tip else ''}"
