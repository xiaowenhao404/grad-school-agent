"""天气查询工具。

用 OpenWeather API；未配置 API key 时返回友好的"暂不支持"提示。
"""
from __future__ import annotations

# from langchain_core.tools import tool

from .registry import registry


# @tool
# @registry.register
def weather_query(city: str, country_code: str | None = None) -> dict:
    """查询城市当前天气。

    Returns:
        {"city": str, "condition": str, "temp_c": float, "source": "api"|"unavailable"}
    """
    # TODO:
    # 1. 读 OPENWEATHER_API_KEY
    # 2. 不存在 -> 返回 source='unavailable'
    # 3. 调 OpenWeather API
    raise NotImplementedError
