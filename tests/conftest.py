"""pytest 共享 fixtures。"""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_graph_state() -> dict:
    """提供测试用的最小 GraphState。"""
    return {
        "user_id": 1,
        "conversation_id": 1,
        "user_input": "test",
        "user_profile": {},
        "memory_enabled": True,
        "messages": [],
    }
