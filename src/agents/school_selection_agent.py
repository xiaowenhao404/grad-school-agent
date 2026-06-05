"""SchoolSelectionAgent — 选校机器人（多轮偏好持久化版）。"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

FIELD_LABELS = {
    "tuition_range": "学费区间（USD/年）",
    "qs_rank_range": "QS 排名范围",
    "country": "目标国家和地区",
    "major_category": "专业方向",
    "duration_max": "项目时长上限（月）",
    "language_score": "语言成绩（IELTS/TOEFL）",
}

# 是否触发推荐：专业 OR 国家 OR QS 任意一个有就出结果
def _has_any_locator(prefs: dict) -> bool:
    return bool(
        prefs.get("country")
        or prefs.get("qs_rank_range")
        or prefs.get("major_category")
    )


class SchoolSelectionAgent(BaseAgent):
    name = "school_selection"
    label_zh = "选校机器人"
    prompt_file = "school_selection.txt"

    def run(self, state: "GraphState") -> "GraphState":
        from src.db.engine import get_engine
        from src.db.repositories.school_repo import SchoolProgramRepository
        from src.db.repositories.user_repo import UserRepository
        from src.rag.collections import CollectionName
        from src.rag.retrieval.retriever_factory import get_retriever

        # ── 1. 加载累积偏好（来自 user_profile.school_prefs + 本轮 metadata）
        user_id = state.get("user_id", 1)
        profile_prefs = (state.get("user_profile") or {}).get("school_prefs", {}) or {}
        meta = state.setdefault("metadata", {})
        prefs: dict = meta.setdefault("school_prefs", dict(profile_prefs))

        self._trace(state, "正在解析您本轮的选校偏好…")

        # ── 2. LLM 抽取新偏好
        extract_prompt = (
            "从【本轮用户输入】抽取选校偏好，只输出 JSON（字段缺失置 null，不要瞎猜）：\n"
            '{"school_name":"","tuition_range":[min,max],"qs_rank_range":[min,max],"country":"","major_category":"","duration_max":null,"language_score":{"ielts":null,"toefl":null}}\n\n'
            "解析规则（重要）：\n"
            "- **学校精确匹配**：用户提到具体学校名（『斯坦福/MIT/清华/Stanford/麻省理工』等），写入 school_name（保留用户原词）\n"
            "- 『QS 第一/全球第一/Top1』⇒ qs_rank_range=[1,1]\n"
            "- 『QS 1-20』⇒ [1,20]；『Top10/前十』⇒ [1,10]；『Top50』⇒ [1,50]\n"
            "- 『常春藤』⇒ country=美国, qs_rank_range=[1,50]\n"
            "- 『英国/美国/香港/澳洲/新加坡/欧洲』⇒ country=对应名词\n"
            "- CS/AI/数据科学/机器学习 ⇒ major_category=计算机；金融工程 ⇒ 金融；MBA ⇒ 商科\n"
            "- 学费『50万人民币以内』⇒ tuition_range=[0, 71429]（÷7 转 USD）\n"
            "- **语言成绩识别（重要）**：\n"
            "  · 『雅思 7』『IELTS 7.0』『ielts7.5』 ⇒ language_score={\"ielts\":7.0, \"toefl\":null}\n"
            "  · 『托福 100』『TOEFL 105』 ⇒ language_score={\"ielts\":null, \"toefl\":100}\n"
            "  · 同时提到 ⇒ 两者都填\n"
            "- 学制：『1 年/12 个月以内』⇒ duration_max=12；『2 年内』⇒ 24\n"
            "- 用户没提到的字段一律 null，绝对不要编造\n\n"
            f"【本轮用户输入】{state.get('user_input','')}"
        )
        raw = self._safe_llm_chat(state, [{"role": "user", "content": extract_prompt}],
                                  response_format={"type": "json_object"})
        new_prefs = self._extract_json(raw["content"]) if raw else {}

        # ── 3. 合并到累积偏好（覆盖语义）
        for k, v in new_prefs.items():
            if v in (None, "", [], {}):
                continue
            if isinstance(v, dict):
                old = prefs.get(k) or {}
                if isinstance(old, dict):
                    for ik, iv in v.items():
                        if iv not in (None, "", [], {}):
                            old[ik] = iv
                    prefs[k] = old
                else:
                    prefs[k] = v
            else:
                prefs[k] = v

        # ── 4. 持久化（写回 user_profile.school_prefs，下一轮 pre_hook 自动加载）
        if state.get("memory_enabled", True):
            try:
                UserRepository().update_profile(user_id, {"school_prefs": prefs})
            except Exception:
                pass

        zh_summary = "、".join(
            f"{FIELD_LABELS.get(k, k)}={v}"
            for k, v in prefs.items() if v not in (None, "", [], {})
        )
        if zh_summary:
            self._trace(state, f"已累积偏好：{zh_summary}")

        # ── 4.5 specific_name 直达：用户指定了具体学校，立即按学校精确查询，跳过宽松校验
        if prefs.get("school_name"):
            from src.db.repositories.school_repo import SchoolRepository
            sname = prefs["school_name"]
            self._trace(state, f"识别到具体学校名「{sname}」，直接精确匹配…")
            schools = SchoolRepository(engine=get_engine()).search_by_name(sname, limit=3)
            if schools:
                target_school = schools[0]
                sn_disp = (target_school.get("names") or [sname])
                if isinstance(sn_disp, str):
                    import ast
                    try: sn_disp = ast.literal_eval(sn_disp)
                    except Exception: sn_disp = [sn_disp]
                self._trace(state, f"匹配到：{sn_disp[0] if sn_disp else sname}，正在拉取其所有项目…")
                # 用 school_id 强约束 + 其他偏好仅作可选过滤
                direct_filter = {"school_id": target_school["id"]}
                if prefs.get("major_category"):
                    direct_filter["major_category"] = prefs["major_category"]
                if prefs.get("language_score"):
                    direct_filter["language_score"] = prefs["language_score"]
                program_ids = SchoolProgramRepository(engine=get_engine()).filter_programs(direct_filter, limit=10)
                # 若加专业过滤后空，回退到只按 school_id
                if not program_ids:
                    program_ids = SchoolProgramRepository(engine=get_engine()).filter_programs({"school_id": target_school["id"]}, limit=10)
                # 跳过宽松校验，直接进入卡片渲染（复用下方逻辑）
                state["__direct_program_ids"] = program_ids
                state["__direct_school_match"] = target_school
            else:
                self._trace(state, f"未在数据库中找到「{sname}」，回退到通用偏好检索。")

        # ── 5. 宽松校验：至少有一个可用条件（专业 / 国家 / QS / 具体学校名）
        if not _has_any_locator(prefs) and not state.get("__direct_program_ids"):
            ask = (
                "请告诉我您的选校倾向，可以是以下任意一种：\n"
                "- 目标国家或地区（如：美国、英国、香港）\n"
                "- QS 排名（如：前 50、Top10、QS 第一）\n"
                "- 专业方向（如：CS、AI、金融）\n"
                "- 或直接告诉我具体学校名（如：斯坦福、MIT）\n\n"
                "💡 可以分多轮慢慢补充，我会记住每一条偏好。"
            )
            state["agent_response"] = ask
            self._append_message(state, "assistant", ask)
            return state

        # ── 6. SQL 过滤候选（若已经走 school_name 直达，直接使用其结果）
        repo = SchoolProgramRepository(engine=get_engine())
        if state.get("__direct_program_ids"):
            program_ids = state.pop("__direct_program_ids")
            state.pop("__direct_school_match", None)
        else:
            self._trace(state, "正在数据库中根据累积偏好过滤候选项目…")
            program_ids = repo.filter_programs(prefs, limit=50)

        # 兜底：单条件太苛刻时逐步放宽
        if not program_ids and prefs.get("qs_rank_range") and prefs.get("major_category"):
            self._trace(state, "未匹配，自动放宽 QS 范围再试…")
            fallback = dict(prefs); fallback.pop("qs_rank_range", None)
            program_ids = repo.filter_programs(fallback, limit=50)
        if not program_ids and prefs.get("tuition_range"):
            self._trace(state, "未匹配，自动放宽学费上限再试…")
            fallback = dict(prefs); fallback.pop("tuition_range", None)
            program_ids = repo.filter_programs(fallback, limit=50)

        if not program_ids:
            reply = (
                "根据您当前的偏好暂未找到匹配项目。\n\n"
                "💡 试试调整其中一个条件：换个国家、放宽 QS 排名、或换个专业方向。"
            )
            self._trace(state, "仍未找到匹配项目。")
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            return state

        self._trace(state, f"过滤得到 {len(program_ids)} 个候选项目，正在做语义排序…")

        # ── 7. 语义排序（Top3）— 检索失败时优雅降级到 SQL 顺序
        where = {"program_id": {"$in": program_ids}, "chunk_type": "program"}
        query = " ".join(filter(None, [
            prefs.get("country", ""), prefs.get("major_category", ""), "硕士项目",
        ]))
        results = []
        try:
            retriever = get_retriever(CollectionName.SCHOOLS)
            results = retriever.search(query, top_k_final=3, where=where)
        except Exception as e:
            self._trace(state, f"⚠️ 向量库检索失败：{type(e).__name__}，已回退为 SQL 顺序。")
        if not results:
            # 向量召回为空 / 失败 → 直接按 SQL 顺序取前 3
            results = []
            for pid in program_ids[:3]:
                results.append(type("R", (), {"metadata": {"program_id": pid}, "content": ""})())
            self._trace(state, f"已按 SQL 排序选取 Top {len(results)} 推荐。")
        else:
            self._trace(state, f"语义排序完成，挑选 Top {len(results)} 推荐。")

        cards = []
        for r in results:
            m = getattr(r, "metadata", {}) or {}
            pid = m.get("program_id")
            prog = repo.get_program_with_school(pid) if pid else None
            if prog:
                pnames = prog.get("program_names") or []
                if isinstance(pnames, str):
                    import ast
                    try:
                        pnames = ast.literal_eval(pnames)
                    except Exception:
                        pnames = [pnames]
                snames = prog.get("names") or []
                if isinstance(snames, str):
                    import ast
                    try:
                        snames = ast.literal_eval(snames)
                    except Exception:
                        snames = [snames]
                # 学费换算成 CNY（调用 currency tool, 实时汇率优先）
                tuition_native = prog.get("tuition_per_year")
                native_ccy = (prog.get("currency") or "USD").upper()
                tuition_cny_str = ""
                if tuition_native and native_ccy != "CNY":
                    try:
                        from src.tools.currency_tool import currency_convert
                        conv = currency_convert(float(tuition_native), native_ccy, "CNY")
                        if conv.get("source") in ("live", "fallback"):
                            tuition_cny_str = f"（≈ ¥{int(conv['amount']):,}/年）"
                            if not getattr(self, "_currency_trace_logged", False):
                                self._trace(state, f"💱 调用 currency 工具：{native_ccy}→CNY 汇率 = {conv['rate']:.4f}（{conv['source']}）")
                                self._currency_trace_logged = True
                    except Exception:
                        pass

                card = (
                    f"### 🏫 {snames[0] if snames else '?'} — {pnames[0] if pnames else '?'}\n"
                    f"> {prog.get('description_short') or '—'}\n\n"
                    f"- 🌍 **国家**：{prog.get('country','?')}　**QS**：{prog.get('qs_rank','—')}\n"
                    f"- 💰 **学费**：{tuition_native} {native_ccy}/年 {tuition_cny_str}　**学制**：{prog.get('duration_months')} 个月\n"
                    f"- 🎓 **语言**：IELTS≥{prog.get('ielts_min') or '—'}　TOEFL≥{prog.get('toefl_min') or '—'}\n"
                    f"- 🔗 [项目主页]({prog.get('program_url') or prog.get('official_site') or '#'})　·　[📖 完整介绍](#program-{pid})"
                )
            else:
                card = f"### 项目 {pid}\n（未取到详细信息）"
            cards.append(card)

        reply = "根据您累积的偏好，为您匹配到以下项目：\n\n" + "\n\n".join(cards)

        # 条件追问：仅追问还没填的可选字段
        missing_optional = []
        if not prefs.get("tuition_range"):
            missing_optional.append("学费上限")
        ls = prefs.get("language_score") or {}
        if not ls.get("ielts") and not ls.get("toefl"):
            missing_optional.append("语言成绩（IELTS/TOEFL）")
        if not prefs.get("duration_max"):
            missing_optional.append("学制偏好")
        if missing_optional:
            reply += f"\n\n💡 想要更精准的结果？还可以告诉我：{'、'.join(missing_optional)}。"

        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state
