"""汇率换算工具。

外部 API 不可用时回退到 settings.tools.currency.fallback_rates 静态表。
"""
from __future__ import annotations

# from langchain_core.tools import tool

from .registry import registry


# @tool
# @registry.register
def currency_convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """将 amount 从 from_currency 换算为 to_currency。

    Returns:
        {"amount": float, "from": str, "to": str, "rate": float, "source": "api"|"fallback"}
    """
    # TODO:
    # 1. 优先调用外部 API（用 EXCHANGE_RATE_API_KEY）
    # 2. API 不可用时使用 fallback_rates
    # 3. 返回结构化 dict
    raise NotImplementedError
