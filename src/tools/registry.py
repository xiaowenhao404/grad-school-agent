"""工具注册中心。

详见 DEV_SPEC.md 3.3 节。

设计要点：
- in-process 注册 LangChain @tool 装饰的函数
- 预留 MCP Server 接入抽象点：未来可把 ToolRegistry 替换为 MCP client，
  上层 Agent 调用接口不变
"""
from __future__ import annotations

from typing import Any, Callable


class ToolRegistry:
    """工具注册中心，单例模式。"""

    def __init__(self):
        self._tools: dict[str, Callable] = {}

    def register(self, tool_fn: Callable) -> Callable:
        """注册工具（可用作装饰器）。

        要求 tool_fn 是 LangChain @tool 装饰过的函数（具有 .name 属性）。
        """
        name = getattr(tool_fn, "name", tool_fn.__name__)
        self._tools[name] = tool_fn
        return tool_fn

    def get(self, name: str) -> Callable | None:
        return self._tools.get(name)

    def list_all(self) -> list[Callable]:
        """返回全部工具，供 Agent 绑定到 LLM。"""
        return list(self._tools.values())

    def describe(self) -> list[dict[str, Any]]:
        """返回工具的 schema 描述，供 prompt 注入或 debug。"""
        return [
            {
                "name": getattr(t, "name", t.__name__),
                "description": getattr(t, "description", ""),
            }
            for t in self._tools.values()
        ]


# 全局单例
registry = ToolRegistry()


def autoload_tools() -> None:
    """启动时调用，触发各 tool 模块的 import 完成 @registry.register。"""
    # 导入即注册（依赖模块顶层的 registry.register 装饰器）
    from . import currency_tool  # noqa: F401
    from . import tuition_tool  # noqa: F401
    from . import weather_tool  # noqa: F401
