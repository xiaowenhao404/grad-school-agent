"""SkillRegistry — 自动发现与聚合 Runtime Skills。

发现规则：扫描 src/runtime_skills/ 的所有子包，
        其 __init__.py 中所有 BaseRuntimeSkill 实例都会被注册。
"""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from .base import BaseRuntimeSkill


class SkillRegistry:
    def __init__(self):
        self._skills: list[BaseRuntimeSkill] = []

    def register(self, skill: BaseRuntimeSkill) -> None:
        self._skills.append(skill)

    def list_all(self) -> list[BaseRuntimeSkill]:
        return list(self._skills)

    def collect_context(self, query: str, context: dict) -> str:
        """聚合所有命中 skill 的注入内容。

        Returns:
            拼接后的文本（按 skill name 排序、用 markdown 分节）；
            无命中时返回空字符串。
        """
        chunks: list[str] = []
        for skill in self._skills:
            try:
                if skill.match(query, context):
                    snippet = skill.provide_context(query, context)
                    if snippet:
                        chunks.append(f"### {skill.name}\n{snippet}")
            except Exception:  # noqa: BLE001
                # 单个 skill 失败不能影响整体对话
                continue
        return "\n\n".join(chunks)

    def discover(self) -> None:
        """扫描子包并触发 import 完成注册。"""
        pkg_dir = Path(__file__).parent
        for _, module_name, is_pkg in pkgutil.iter_modules([str(pkg_dir)]):
            if not is_pkg:
                continue
            full_name = f"src.runtime_skills.{module_name}"
            importlib.import_module(full_name)


# 全局单例
skill_registry = SkillRegistry()
