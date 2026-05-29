"""配置加载 — 读取 config/settings.yaml + .env，合并为 Settings dict。"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv


def get_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "settings.yaml"


@lru_cache(maxsize=1)
def load_settings() -> dict:
    """加载配置（单例缓存）。env 变量覆盖 yaml 中对应的敏感字段。"""
    # 加载 .env（不存在时静默跳过）
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path, override=True)

    with open(get_config_path(), encoding="utf-8") as f:
        cfg: dict = yaml.safe_load(f)

    # env 覆盖规则：LLM_API_KEY → cfg["llm"]["api_key"] 等
    _env_overrides = {
        "LLM_API_KEY":        ("llm", "api_key"),
        "LLM_BASE_URL":       ("llm", "base_url"),
        "LLM_MODEL":          ("llm", "model"),
        "LLM_PROVIDER":       ("llm", "provider"),
        "EMBEDDING_PROVIDER": ("embedding", "provider"),
        "EMBEDDING_API_KEY":  ("embedding", "api_key"),
        "EMBEDDING_BASE_URL": ("embedding", "base_url"),
        "EMBEDDING_MODEL":    ("embedding", "model"),
        "EXCHANGE_RATE_API_KEY": ("tools", "currency", "api_key"),
        "OPENWEATHER_API_KEY":   ("tools", "weather", "api_key"),
    }
    for env_key, path in _env_overrides.items():
        val = os.getenv(env_key)
        if val:
            node = cfg
            for part in path[:-1]:
                node = node.setdefault(part, {})
            node[path[-1]] = val

    return cfg
