"""工具注册中心（进程内 MCP-like 调用层）。

本模块是工具实现的**唯一注册处**，对外暴露 MCP 风格的两个核心 API：
- `list_tools()` → 返回 `[{name, description, inputSchema}, ...]`
- `call_tool(name, **args)` → 同步调用对应工具并返回 dict

设计要点：
- in-process 模式：与 Flask 同进程，供 LangGraph Agent 直接调用，避免序列化开销；
  这不是 MCP 协议本身（没有 JSON-RPC 帧、没有 transport），故标注 `mcp-like/0.1`
- 含 JSON Schema 描述，可供 LLM function-calling 直接消费

**真正的标准 MCP Server 见 `src/mcp_server/`**：它基于官方 mcp Python SDK，
以 JSON-RPC over stdio 对外服务，并且直接复用本注册中心里的同一批函数实现
（工具名/描述/参数说明都取自 `list_tools()`）。因此新增工具只需在这里注册一次，
两条暴露路径会同时生效。

详见 DEV_SPEC.md 3.3 节。
"""
from __future__ import annotations

from typing import Any, Callable


# 内置工具 schema（JSON Schema 子集，与 MCP 规范一致）
_TOOL_SCHEMAS: dict[str, dict] = {
    "currency_convert": {
        "description": "实时汇率换算。优先调 open.er-api.com（免 key），失败回退静态表。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "金额"},
                "from_currency": {"type": "string", "description": "源币种 ISO 代码，如 USD/GBP/CNY"},
                "to_currency": {"type": "string", "description": "目标币种 ISO 代码"},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
    "weather_query": {
        "description": "实时天气查询。优先调 wttr.in（免 key，中文），失败回退 OpenWeather。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市英文名，如 Shanghai / London"},
                "country_code": {"type": "string", "description": "可选国家代码，如 US / CN"},
            },
            "required": ["city"],
        },
    },
    "tuition_estimate": {
        "description": "估算指定项目的总学费（含汇率换算到目标币种）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "program_id": {"type": "integer", "description": "school_programs 表的项目 ID"},
                "target_currency": {"type": "string", "description": "目标币种，默认 CNY"},
            },
            "required": ["program_id"],
        },
    },
}


class ToolRegistry:
    """MCP-like 工具注册中心，单例模式。

    实现的 MCP 兼容 API:
    - list_tools() → MCP 标准格式的 tool 描述
    - call_tool(name, **args) → 同步调用并返回 dict
    """

    SERVER_NAME = "grad-school-tools"  # MCP server 标识
    PROTOCOL_VERSION = "mcp-like/0.1"  # 标明这是 MCP-like 而非完整 MCP 实现

    def __init__(self):
        self._tools: dict[str, Callable] = {}

    def register(self, tool_fn: Callable) -> Callable:
        """注册工具（可用作装饰器）。"""
        name = getattr(tool_fn, "name", tool_fn.__name__)
        self._tools[name] = tool_fn
        return tool_fn

    def get(self, name: str) -> Callable | None:
        return self._tools.get(name)

    def list_all(self) -> list[Callable]:
        """返回全部工具函数。"""
        return list(self._tools.values())

    def list_tools(self) -> list[dict[str, Any]]:
        """**MCP 标准接口**：返回工具 schema 列表，与 Anthropic MCP SDK 的
        `mcp.list_tools()` 输出格式一致。

        每项形如 `{name, description, inputSchema}`，可直接喂给 LLM tool_choice。
        """
        items = []
        for name, fn in self._tools.items():
            schema = _TOOL_SCHEMAS.get(name, {})
            items.append({
                "name": name,
                "description": schema.get("description") or getattr(fn, "__doc__", "") or "",
                "inputSchema": schema.get("inputSchema") or {"type": "object", "properties": {}},
            })
        return items

    def call_tool(self, name: str, _trace_cb: Callable[[str], None] | None = None,
                  **arguments) -> dict[str, Any]:
        """**MCP 标准接口**：通过工具名调用并返回 dict，与 Anthropic MCP SDK 的
        `mcp.call_tool(name, arguments)` 行为一致。

        额外参数 `_trace_cb(text)`：调用前注入一条 trace（用于 SSE 工作流可视化）。
        """
        fn = self._tools.get(name)
        if fn is None:
            raise ValueError(f"unknown tool: {name}")
        if _trace_cb:
            _trace_cb(f"📡 [MCP] 调用工具 `{name}` (args={arguments})")
        result = fn(**arguments)
        if not isinstance(result, dict):
            result = {"result": result}
        return result

    def describe(self) -> list[dict[str, Any]]:
        """兼容旧 API（等同 list_tools 的简化版）。"""
        return [{"name": t["name"], "description": t["description"]} for t in self.list_tools()]


# 全局单例
registry = ToolRegistry()


def autoload_tools() -> None:
    """启动时调用，触发各 tool 模块的 import 完成 @registry.register。"""
    from . import currency_tool  # noqa: F401
    from . import tuition_tool  # noqa: F401
    from . import weather_tool  # noqa: F401
