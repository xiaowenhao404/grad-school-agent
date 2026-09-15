"""标准 MCP（Model Context Protocol）Server —— stdio transport。

与 `src/tools/registry.py` 里的进程内 `ToolRegistry` 是**同一份工具实现的两种暴露方式**：

- `ToolRegistry`：in-process 调用，供 LangGraph Agent 在 Flask 进程内直接调用；
- 本模块：基于官方 `mcp` Python SDK 的独立进程 server，走 JSON-RPC over stdio，
  供任意外部 MCP Client（Claude Desktop / Cursor / MCP Inspector / SDK client）接入。

实现约束（刻意为之）：
- 工具函数**直接 import 现有实现**（`currency_convert` / `weather_query` /
  `tuition_estimate`），不复制粘贴，也不重写业务逻辑；
- 工具的 name / description / 参数说明统一取自 `registry.list_tools()`，
  保证两条暴露路径对外描述完全一致；新增工具只需注册到 `ToolRegistry`，
  MCP Server 会自动同步暴露。

注意：mcp SDK 2.x 已把 v1 的 `FastMCP` 重命名为 `MCPServer`
（`mcp.server.mcpserver.MCPServer`），本模块按 2.x API 编写。
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer

from src.tools.registry import autoload_tools, registry

SERVER_VERSION = "0.1.0"

INSTRUCTIONS = """Grad-School-Agent 申研选校助手的外部工具集。

提供三个工具：
- currency_convert：实时汇率换算（留学费用估算常用）
- weather_query：目标城市天气查询
- tuition_estimate：按 program_id 估算项目总学费并换算币种

tuition_estimate 依赖本仓库的 SQLite 数据库 data/grad_school.db，
因此启动 server 时必须把工作目录设为项目根目录。
"""

logger = logging.getLogger(__name__)


def _resolve_impl(name: str) -> Callable[..., Any]:
    """从 ToolRegistry 取出工具的真实实现函数（而不是另写一份）。"""
    fn = registry.get(name)
    if fn is None:  # pragma: no cover - autoload 之后不应发生
        raise RuntimeError(f"tool not found in ToolRegistry: {name}")
    return fn


def _merge_param_descriptions(auto_schema: dict, declared_schema: dict) -> dict:
    """把 ToolRegistry 手写 schema 里的参数说明合并进 SDK 自动生成的 JSON Schema。

    参数的**类型与必填性**仍以函数签名自动推导为准（这也是 SDK 校验入参的依据），
    这里只补 description，避免两份 schema 各写各的而产生漂移。
    """
    declared_props = (declared_schema or {}).get("properties") or {}
    auto_props = (auto_schema or {}).get("properties") or {}
    for key, declared in declared_props.items():
        desc = declared.get("description")
        if desc and key in auto_props and not auto_props[key].get("description"):
            auto_props[key]["description"] = desc
    return auto_schema


def build_server() -> MCPServer:
    """构造并返回配置好三个工具的 MCPServer 实例。"""
    autoload_tools()

    server = MCPServer(
        name=registry.SERVER_NAME,
        title="Grad School Agent Tools",
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
    )

    for spec in registry.list_tools():
        name = spec["name"]
        server.add_tool(
            _resolve_impl(name),
            name=name,
            description=spec["description"],
        )
        # 用手写 schema 的参数说明补齐自动生成的 inputSchema
        tool = server._tool_manager.get_tool(name)
        if tool is not None:
            _merge_param_descriptions(tool.parameters, spec.get("inputSchema") or {})

    return server


def main() -> None:
    """stdio 模式入口。

    stdout 被 JSON-RPC 帧独占，所有日志必须走 stderr，否则会破坏协议帧。
    """
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_server().run(transport="stdio")
