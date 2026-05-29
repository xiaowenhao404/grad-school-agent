"""Runtime Skills 插件层。

详见 DEV_SPEC.md 3.6 节、7.2 节。

设计思想：将领域知识与 Agent 解耦。Agent 通过 SkillRegistry 查询命中的 skill，
把 skill 提供的额外知识/规则注入 prompt。

新增 skill 步骤：
1. 在本目录下新建子包（如 `uk_psw_policy/`）
2. 在子包 `__init__.py` 中实现 BaseRuntimeSkill 并实例化为模块级变量
3. 重启系统，SkillRegistry 自动发现
"""

from .base import BaseRuntimeSkill
from .registry import SkillRegistry, skill_registry

__all__ = ["BaseRuntimeSkill", "SkillRegistry", "skill_registry"]
