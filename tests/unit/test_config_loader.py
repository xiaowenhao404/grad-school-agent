"""单测：config_loader — yaml+env 合并优先级。"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def _reload():
    """清除 lru_cache 后重新导入，确保每次测试独立。"""
    from src.utils import config_loader
    config_loader.load_settings.cache_clear()
    return config_loader.load_settings


def test_loads_yaml_defaults():
    cfg = _reload()()
    assert cfg["llm"]["model"] == "deepseek-chat"
    assert cfg["retrieval"]["hybrid"]["rrf_k"] == 60


def test_env_overrides_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    cfg = _reload()()
    assert cfg["llm"]["api_key"] == "test-key-123"


def test_missing_env_does_not_crash(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    cfg = _reload()()
    assert "api_key" not in cfg.get("llm", {}) or cfg["llm"].get("api_key") != "test-key-123"


def test_returns_dict():
    cfg = _reload()()
    assert isinstance(cfg, dict)
    assert "llm" in cfg and "embedding" in cfg and "db" in cfg
