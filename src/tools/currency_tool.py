"""汇率换算工具（静态降级表，demo 不挂网）。"""
from __future__ import annotations

from .registry import registry


def currency_convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """将 amount 从 from_currency 换算为 to_currency。"""
    from src.utils.config_loader import load_settings
    rates: dict = load_settings()["tools"]["currency"]["fallback_rates"]
    key = f"{from_currency.upper()}_{to_currency.upper()}"
    rev_key = f"{to_currency.upper()}_{from_currency.upper()}"
    if key in rates:
        rate = rates[key]
    elif rev_key in rates:
        rate = 1.0 / rates[rev_key]
    elif from_currency.upper() == to_currency.upper():
        rate = 1.0
    else:
        rate = 1.0  # 未知组合，原样返回
    return {"amount": round(amount * rate, 2), "from": from_currency, "to": to_currency,
            "rate": rate, "source": "fallback"}


registry.register(currency_convert)

