"""SchoolSelectionAgent — 选校机器人。"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState

REQUIRED_PREFS = ("tuition_range", "qs_rank_range", "country", "major_category")


class SchoolSelectionAgent(BaseAgent):
    name = "school_selection"
    prompt_file = "school_selection.txt"

    def run(self, state: "GraphState") -> "GraphState":
        from src.db.engine import get_engine
        from src.db.repositories.school_repo import SchoolProgramRepository
        from src.rag.collections import CollectionName
        from src.rag.retrieval.retriever_factory import get_retriever

        meta = state.setdefault("metadata", {})
        prefs: dict = meta.setdefault("school_prefs", {})

        llm = self._get_llm()
        extract_prompt = (
            "从用户输入中提取选校偏好，输出 JSON（缺失字段用 null）：\n"
            '{"tuition_range":[min,max],"qs_rank_range":[min,max],"country":"","major_category":"","duration_max":null,"language_score":{}}\n'
            f"用户输入：{state.get('user_input', '')}"
        )
        try:
            raw = llm.chat([{"role": "user", "content": extract_prompt}],
                           response_format={"type": "json_object"})
            new_prefs = json.loads(raw["content"])
            for k, v in new_prefs.items():
                if v is not None and v != [] and v != {}:
                    prefs[k] = v
        except Exception:
            pass

        missing = [k for k in REQUIRED_PREFS if not prefs.get(k)]
        if missing:
            ask = f"请告诉我您的偏好：{', '.join(missing[:2])}（例如：学费区间、目标国家、专业方向、QS排名范围）"
            state["agent_response"] = ask
            self._append_message(state, "assistant", ask)
            return state

        repo = SchoolProgramRepository(engine=get_engine())
        program_ids = repo.filter_programs(prefs, limit=50)
        if not program_ids:
            reply = "根据您的条件暂未找到匹配项目，建议放宽学费区间或QS排名范围。"
            state["agent_response"] = reply
            self._append_message(state, "assistant", reply)
            return state

        where = {"program_id": {"$in": program_ids}, "chunk_type": "program"}
        query = f"{prefs.get('country','')} {prefs.get('major_category','')} 硕士项目"
        retriever = get_retriever(CollectionName.SCHOOLS)
        results = retriever.search(query, top_k_final=3, where=where)

        cards = []
        for r in results:
            m = r.metadata
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
                card = (
                    f"### {snames[0] if snames else '?'} — {pnames[0] if pnames else '?'}\n"
                    f"- 学费：{prog.get('tuition_per_year')} {prog.get('currency')}/年，学制：{prog.get('duration_months')}个月\n"
                    f"- 语言：IELTS≥{prog.get('ielts_min')}，TOEFL≥{prog.get('toefl_min')}\n"
                    f"- 链接：{prog.get('program_url') or prog.get('official_site') or '暂无'}"
                )
            else:
                card = f"### 项目 {pid}\n{r.content[:120]}..."
            cards.append(card)

        reply = "为您匹配到以下项目：\n\n" + "\n\n".join(cards)
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state
