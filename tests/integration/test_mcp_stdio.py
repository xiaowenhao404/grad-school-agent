"""端到端验证：以真实子进程 + stdio transport 连接本项目的 MCP Server。

覆盖 initialize 握手、tools/list、tools/call 三个 JSON-RPC 往返。
"""
from __future__ import annotations

import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server"],
        cwd=str(_PROJECT_ROOT),
        env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )


async def _roundtrip() -> dict:
    async with Client(_params(), raise_exceptions=True) as client:
        listed = await client.list_tools()
        called = await client.call_tool(
            "currency_convert",
            {"amount": 100, "from_currency": "USD", "to_currency": "USD"},
        )
        return {
            "server_name": client.server_info.name,
            "tool_names": sorted(t.name for t in listed.tools),
            "is_error": called.is_error,
            "text": called.content[0].text if called.content else "",
        }


def test_stdio_roundtrip() -> None:
    out = anyio.run(_roundtrip)
    assert out["server_name"] == "grad-school-tools"
    assert out["tool_names"] == ["currency_convert", "tuition_estimate", "weather_query"]
    assert out["is_error"] is False
    assert "identical" in out["text"]
