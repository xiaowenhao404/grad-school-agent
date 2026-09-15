"""标准 MCP Server 包 —— 把仓库内已有工具通过 MCP 协议对外暴露。

入口：`python -m src.mcp_server`（stdio transport）。
"""

from .server import SERVER_VERSION, build_server, main

__all__ = ["SERVER_VERSION", "build_server", "main"]
