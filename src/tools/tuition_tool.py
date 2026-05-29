"""学费估算工具。"""
from __future__ import annotations

import math

from .currency_tool import currency_convert
from .registry import registry


def tuition_estimate(program_id: int, target_currency: str = "CNY") -> dict:
    """估算指定项目的总学费（含汇率换算）。"""
    from src.db.engine import get_engine
    from src.db.repositories.school_repo import SchoolProgramRepository
    repo = SchoolProgramRepository(engine=get_engine())
    prog = repo.get(program_id)
    if not prog:
        return {"error": f"program_id={program_id} not found"}
    tuition = prog["tuition_per_year"]
    currency = prog["currency"]
    months = prog["duration_months"]
    total_years = math.ceil(months / 12)
    total_original = tuition * total_years
    converted = currency_convert(total_original, currency, target_currency)
    return {
        "program_id": program_id,
        "tuition_per_year": {"amount": tuition, "currency": currency},
        "duration_months": months,
        "total_original": {"amount": total_original, "currency": currency},
        "total_target": {"amount": converted["amount"], "currency": target_currency},
    }


registry.register(tuition_estimate)

