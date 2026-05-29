"""ConsultantAgent — 咨询机器人。"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState


class ConsultantAgent(BaseAgent):
    name = "consultant"
    prompt_file = "consultant.txt"

    def run(self, state: "GraphState") -> "GraphState":
        from src.rag.collections import CollectionName
        from src.rag.retrieval.retriever_factory import get_retriever
        from src.runtime_skills.registry import skill_registry

        query = state.get("user_input", "")
        retriever = get_retriever(CollectionName.INTERNAL_DOCS)
        results = retriever.search(query, top_k_final=5)
        retrieved_chunks = "\n\n".join(
            f"[来源: {r.metadata.get('source', r.chunk_id)}]\n{r.content}"
            for r in results
        )
        skill_context = skill_registry.collect_context(query, state)
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
        llm = self._get_llm()
        resp = llm.chat([{"role": "user", "content": prompt}])
        reply = resp["content"]
        state["agent_response"] = reply
        self._append_message(state, "assistant", reply)
        return state

