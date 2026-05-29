"""学费估算工具。

输入项目 ID 与目标币种，结合 school_programs.tuition_per_year + currency_convert
返回总学费估算（含汇率换算）。
"""
from __future__ import annotations

# from langchain_core.tools import tool

from .currency_tool import currency_convert
from .registry import registry


# @tool
# @registry.register
def tuition_estimate(program_id: int, target_currency: str = "CNY") -> dict:
    """估算指定项目的总学费。

    Returns:
        {
            "program_id": int,
            "tuition_per_year_original": {"amount": ..., "currency": ...},
            "duration_months": int,
            "total_original": {...},
            "total_target": {...},
        }
    """
    # TODO:
    # 1. SchoolProgramRepository.get(program_id) -> {tuition_per_year, currency, duration_months}
    # 2. total_years = duration_months / 12
    # 3. total_original = tuition_per_year * total_years
    # 4. if target_currency != currency: call currency_convert
    raise NotImplementedError
