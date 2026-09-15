"""标准 MCP Server 单元测试（in-process，不起子进程、不走网络）。

重点验证「一份实现、两种暴露方式」：MCP Server 暴露的工具集与 name/description
必须与进程内 ToolRegistry 完全一致。
"""
from __future__ import annotations

import json

import anyio

from src.mcp_server import build_server
from src.tools.registry import autoload_tools, registry


def test_mcp_server_exposes_same_tools_as_registry() -> None:
    autoload_tools()
    server = build_server()
    tools = anyio.run(server.list_tools)

    mcp_names = {t.name for t in tools}
    registry_names = {t["name"] for t in registry.list_tools()}
    assert mcp_names == registry_names
    assert mcp_names == {"currency_convert", "weather_query", "tuition_estimate"}

    descriptions = {t["name"]: t["description"] for t in registry.list_tools()}
    for tool in tools:
        assert tool.description == descriptions[tool.name]


def test_mcp_input_schema_carries_param_descriptions() -> None:
    server = build_server()
    tools = {t.name: t for t in anyio.run(server.list_tools)}
    props = tools["currency_convert"].input_schema["properties"]
    assert props["amount"]["description"] == "金额"
    assert set(tools["currency_convert"].input_schema["required"]) == {
        "amount",
        "from_currency",
        "to_currency",
    }


def test_mcp_call_tool_reuses_registry_implementation() -> None:
    server = build_server()
    # 同币种走 short-circuit 分支，不触发外网请求
    result = anyio.run(
        lambda: server.call_tool(
            "currency_convert",
            {"amount": 100, "from_currency": "USD", "to_currency": "USD"},
        )
    )
    assert result.is_error is False
    payload = json.loads(result.content[0].text)
    assert payload["source"] == "identical"
    assert payload["amount"] == 100.0
