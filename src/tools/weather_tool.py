"""天气查询工具。

策略：
1. 优先调免 API key 的 wttr.in（支持中文、全球城市），缓存 10min
2. 失败时再尝试 OpenWeather（如设置了 OPENWEATHER_API_KEY）
3. 都失败 → 返回 source='unavailable'
"""
from __future__ import annotations

import os
import time
from .registry import registry

_WEATHER_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 10 * 60  # 10 分钟


def _fetch_wttr(city: str) -> dict | None:
    """wttr.in 免 key 天气服务，?format=j1 返回 JSON。"""
    try:
        import requests
        # ?format=j1 简化 JSON；lang=zh-cn 给中文描述
        url = f"https://wttr.in/{city}?format=j1&lang=zh-cn"
        r = requests.get(url, timeout=5, headers={"User-Agent": "curl/8.0"})
        if r.status_code != 200:
            return None
        d = r.json()
        cur = (d.get("current_condition") or [{}])[0]
        return {
            "city": city,
            "condition": (cur.get("lang_zh-cn") or [{}])[0].get("value")
                         or cur.get("weatherDesc", [{}])[0].get("value", "未知"),
            "temp_c": float(cur.get("temp_C", 0)),
            "feels_c": float(cur.get("FeelsLikeC", 0)),
            "humidity": int(cur.get("humidity", 0)),
            "wind_kmph": float(cur.get("windspeedKmph", 0)),
            "source": "wttr.in",
        }
    except Exception:
        return None


def _fetch_openweather(city: str, country_code: str | None = None) -> dict | None:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None
    try:
        import requests
        q = f"{city},{country_code}" if country_code else city
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": q, "appid": api_key, "units": "metric", "lang": "zh_cn"},
            timeout=5,
        )
        if r.status_code != 200:
            return None
        d = r.json()
        return {
            "city": city,
            "condition": d["weather"][0]["description"],
            "temp_c": d["main"]["temp"],
            "humidity": d["main"]["humidity"],
            "source": "openweather",
        }
    except Exception:
        return None


def weather_query(city: str, country_code: str | None = None) -> dict:
    """查询城市当前天气。优先 wttr.in，回退 OpenWeather。"""
    if not city:
        return {"city": "", "condition": "未指定城市", "source": "unavailable"}
    key = city.strip().lower()
    now = time.time()
    # 缓存命中
    if key in _WEATHER_CACHE:
        ts, data = _WEATHER_CACHE[key]
        if now - ts < _CACHE_TTL:
            return data

    data = _fetch_wttr(city) or _fetch_openweather(city, country_code)
    if data is None:
        return {"city": city, "condition": "天气信息暂不可用",
                "temp_c": None, "source": "unavailable"}
    _WEATHER_CACHE[key] = (now, data)
    return data


registry.register(weather_query)
