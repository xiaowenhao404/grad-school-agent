"""us_visa_knowledge — 美国签证常识 Runtime Skill（示例）。

被 ConsultantAgent 在用户问到美国签证相关问题时自动注入。
"""
from __future__ import annotations

from src.runtime_skills.base import BaseRuntimeSkill
from src.runtime_skills.registry import skill_registry


VISA_KEYWORDS = ("F1", "F-1", "签证", "visa", "DS-160", "USCIS", "I-20")


class UsVisaKnowledge(BaseRuntimeSkill):
    name = "us_visa_knowledge"
    description = "美国 F-1 学生签证流程、材料、面签准备等基础知识。"

    def match(self, query: str, context: dict) -> bool:
        ql = query.lower()
        if "美国" in query or "us" in ql or "usa" in ql or "america" in ql:
            return any(k.lower() in ql for k in VISA_KEYWORDS)
        return False

    def provide_context(self, query: str, context: dict) -> str:
        # TODO: 可改为从 data/raw_docs/internal/us_visa.md 动态读取
        return (
            "美国 F-1 学生签证关键信息：\n"
            "1. 申请前需先拿到 I-20（学校发放）\n"
            "2. 在线填写 DS-160 并缴纳 SEVIS 费 + 签证费\n"
            "3. 预约面签，准备资金证明、学校录取、学业计划等\n"
            "4. 面签结束后等待护照寄回（约 1-2 周）\n"
            "5. 入境时携带 I-20、护照、I-901 收据、录取信原件"
        )


skill_registry.register(UsVisaKnowledge())
