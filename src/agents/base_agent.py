"""Agent 抽象基类。

所有 Agent 继承 BaseAgent 并实现 `run(state) -> state` 方法。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import GraphState


class BaseAgent(ABC):
    """统一 Agent 接口。"""

    #: Agent 名称，会写入 message.agent_name 字段用于追溯
    name: str = "base"

    #: 该 Agent 使用的 prompt 文件名（位于 config/prompts/）
    prompt_file: str | None = None

    @abstractmethod
    def run(self, state: "GraphState") -> "GraphState":
        """处理 state 并返回新的 state。

        每个 Agent 应当：
        1. 从 state 读取必要字段
        2. 调用 LLM / RAG / DB / Tools 完成任务
        3. 把回复写入 state['agent_response']
        4. 在 state['messages'] 追加 assistant message
        5. 返回 state
        """
        raise NotImplementedError
