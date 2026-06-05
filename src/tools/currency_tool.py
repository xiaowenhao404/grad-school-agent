"""汇率换算工具。

策略：
1. 优先调免 API key 的公开服务 `open.er-api.com`（USD base，60s 内缓存）
2. 失败/超时 → 回退到 settings.yaml 的静态 fallback_rates
"""
from __future__ import annotations

import time
from .registry import registry

# 进程内缓存：{base_currency: (timestamp, rates_dict)}
_RATE_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 60 * 60  # 1 小时


def _fetch_rates_online(base: str = "USD") -> dict | None:
    """调 open.er-api.com 拿实时汇率。成功返回 {currency: rate_per_base}；失败返回 None。"""
    base = base.upper()
    now = time.time()
    # 缓存命中
    if base in _RATE_CACHE:
        ts, rates = _RATE_CACHE[base]
        if now - ts < _CACHE_TTL:
            return rates
    try:
        import requests
        # open.er-api.com 免 API key，支持 USD/EUR/GBP/CNY 等所有主流币种
        r = requests.get(f"https://open.er-api.com/v6/latest/{base}", timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("result") != "success":
            return None
        rates = data.get("rates") or {}
        _RATE_CACHE[base] = (now, rates)
        return rates
    except Exception:
        return None


def currency_convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """将 amount 从 from_currency 换算为 to_currency。

    Returns:
        {"amount": float, "from": str, "to": str, "rate": float,
         "source": "live"|"fallback", "as_of": "...（仅 live）"}
    """
    fc = from_currency.upper()
    tc = to_currency.upper()
    if fc == tc:
        return {"amount": round(amount, 2), "from": fc, "to": tc,
                "rate": 1.0, "source": "identical"}

    # 优先尝试实时
    rates = _fetch_rates_online(fc)
    if rates and tc in rates:
        rate = rates[tc]
        return {"amount": round(amount * rate, 2), "from": fc, "to": tc,
                "rate": rate, "source": "live", "as_of": time.strftime("%Y-%m-%d %H:%M", time.localtime())}

    # 回退到静态表
    from src.utils.config_loader import load_settings
    static_rates: dict = load_settings()["tools"]["currency"]["fallback_rates"]
    key = f"{fc}_{tc}"
    rev_key = f"{tc}_{fc}"
    if key in static_rates:
        rate = static_rates[key]
    elif rev_key in static_rates:
        rate = 1.0 / static_rates[rev_key]
    else:
        rate = 1.0  # 未知组合，原样返回
    return {"amount": round(amount * rate, 2), "from": fc, "to": tc,
            "rate": rate, "source": "fallback"}


registry.register(currency_convert)
