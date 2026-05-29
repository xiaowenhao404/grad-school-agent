"""工具层 — LangChain Tool 注册与调用。

Agent 通过 LLM function calling 调用本层工具。
"""

from .registry import ToolRegistry, registry

__all__ = ["ToolRegistry", "registry"]
