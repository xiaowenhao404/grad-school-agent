"""ConsultantAgent — 咨询机器人。"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState


class ConsultantAgent(BaseAgent):
    name = "consultant"
    label_zh = "咨询机器人"
    prompt_file = "consultant.txt"

    def run(self, state: "GraphState") -> "GraphState":
        from src.rag.collections import CollectionName
        from src.rag.retrieval.retriever_factory import get_retriever
        from src.runtime_skills.registry import skill_registry

        query = state.get("user_input", "")
        self._trace(state, f"在多个知识库中检索：「{query[:60]}」…")

        # 同时检索内部文档（top3）+ 老师库（top2）+ 学校库（top2），覆盖三类咨询场景
        chunks: list[tuple[str, str]] = []  # (前缀, content)

        def _safe_search(coll: CollectionName, top_k: int, prefix: str):
            try:
                retriever = get_retriever(coll)
                results = retriever.search(query, top_k_final=top_k)
            except Exception as e:
                self._trace(state, f"⚠️ {prefix} 库检索失败：{type(e).__name__}")
                return
            for r in results:
                src = r.metadata.get("source") or r.metadata.get("name") or r.chunk_id
                chunks.append((f"{prefix}/{src}", r.content))

        _safe_search(CollectionName.INTERNAL_DOCS, 3, "internal")
        _safe_search(CollectionName.TEACHERS, 2, "teachers")
        _safe_search(CollectionName.SCHOOLS, 2, "schools")

        self._trace(state, f"检索到 {len(chunks)} 条相关片段，作为回答依据。")
        retrieved_chunks = "\n\n".join(f"[来源: {src}]\n{txt}" for src, txt in chunks)

        skill_context = skill_registry.collect_context(query, state)
        if skill_context:
            self._trace(state, "已调用工具技能补充上下文（汇率/天气等）。")
        messages_str = "\n".join(
            f"{m['role']}: {m['content']}" for m in state.get("messages", [])[-6:]
        )
        prompt = self._render_prompt(
            user_profile=json.dumps(state.get("user_profile", {}), ensure_ascii=False),
            retrieved_chunks=retrieved_chunks,
            skill_context=skill_context,
            messages=messages_str,
            user_input=query,
        )
        self._trace(state, "正在生成回答…")
        resp = self._safe_llm_chat(state, [{"role": "user", "content": prompt}])
        if resp is None:
            reply = "抱歉，AI 服务暂时不可用，请稍后重试。"
        else:
            reply = resp["content"]
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state

