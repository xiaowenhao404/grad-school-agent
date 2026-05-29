"""天气查询工具（无 API key 时静态降级）。"""
from __future__ import annotations

from .registry import registry


def weather_query(city: str, country_code: str | None = None) -> dict:
    """查询城市当前天气。无 API key 时返回 unavailable。"""
    import os
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"city": city, "condition": "暂不支持天气查询（未配置 API key）",
                "temp_c": None, "source": "unavailable"}
    try:
        import requests
        q = f"{city},{country_code}" if country_code else city
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": q, "appid": api_key, "units": "metric", "lang": "zh_cn"},
            timeout=5,
        )
        data = resp.json()
        return {"city": city, "condition": data["weather"][0]["description"],
                "temp_c": data["main"]["temp"], "source": "api"}
    except Exception:
        return {"city": city, "condition": "天气查询失败", "temp_c": None, "source": "unavailable"}


registry.register(weather_query)

