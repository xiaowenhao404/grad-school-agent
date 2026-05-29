"""ConsultantAgent — 咨询机器人。

详见 DEV_SPEC.md 6.2 节。

职责：通过 Hybrid RAG 检索 `internal_docs` collection，融合命中的 Runtime Skill
注入额外知识，生成带引用的回答。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base_agent import BaseAgent

if TYPE_CHECKING:
    from src.graph.state import GraphState


class ConsultantAgent(BaseAgent):
    name = "consultant"
    prompt_file = "consultant.txt"

    def run(self, state: "GraphState") -> "GraphState":
        # TODO:
        # 1. 用 HybridSearch 检索 internal_docs collection，得到 retrieved_chunks
        # 2. 查询 SkillRegistry，得到 skill_context（命中的 runtime skill 注入文本）
        # 3. 渲染 prompt 并调用 LLM
        # 4. 写入 state['agent_response']，追加 assistant message
        raise NotImplementedError
