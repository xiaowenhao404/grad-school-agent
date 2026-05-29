"""Runtime Skill 抽象接口。

详见 DEV_SPEC.md 3.6 节。
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRuntimeSkill(ABC):
    """运行时领域 skill 抽象基类。

    Attributes:
        name: skill 唯一标识（用作日志/调试）
        description: 一句话描述用途，可被 Agent 用于决定是否启用
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def match(self, query: str, context: dict) -> bool:
        """判断本 skill 是否适用于当前查询。

        Args:
            query: 用户输入文本
            context: 当前 GraphState 的若干上下文字段（user_profile/task_type 等）
        """
        raise NotImplementedError

    @abstractmethod
    def provide_context(self, query: str, context: dict) -> str:
        """返回要注入 prompt 的额外知识/规则文本。

        通常是一段 Markdown 或纯文本。Agent 会把它放入 prompt 的 {skill_context} 占位符。
        """
        raise NotImplementedError
