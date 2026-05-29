# Runtime Skills

> 系统运行时由 Agent 调用的领域知识插件。详见 [`DEV_SPEC.md` 3.6 节](../../DEV_SPEC.md#36-runtime-skills-插件机制)。

## 与 `.claude/skills/` 的区别

| 位置 | 服务对象 | 是否随系统运行 |
|------|---------|--------------|
| `.claude/skills/` | Claude Code（开发期辅助） | 否 |
| `src/runtime_skills/` ← 本目录 | 系统 Agent（运行时） | 是 |

## 如何新增一个 Runtime Skill

1. 在本目录下新建子包，例如 `us_visa_knowledge/`
2. 在子包 `__init__.py` 中实现并实例化 `BaseRuntimeSkill`，调用 `skill_registry.register(...)`
3. 重启系统，`SkillRegistry.discover()` 会自动发现该 skill
4. 适用 Agent（ConsultantAgent / SchoolSelectionAgent）会在生成回复前调用
   `skill_registry.collect_context(query, context)` 取得本 skill 的注入文本

## 模板

```python
# src/runtime_skills/my_new_skill/__init__.py
from src.runtime_skills.base import BaseRuntimeSkill
from src.runtime_skills.registry import skill_registry


class MyNewSkill(BaseRuntimeSkill):
    name = "my_new_skill"
    description = "一句话说明本 skill 提供什么知识/规则"

    def match(self, query: str, context: dict) -> bool:
        # 根据 query 内容或 context（如 task_type）判断是否启用
        return "关键词" in query

    def provide_context(self, query: str, context: dict) -> str:
        return "要注入 prompt 的额外知识或规则（支持 Markdown）"


# 模块加载时自动注册
skill_registry.register(MyNewSkill())
```

## 已有示例

- `us_visa_knowledge/` — 美国签证常识（示例 skill）

## 项目亮点

Runtime Skills 是本项目的工程亮点之一。未来可以扩展：

- `uk_psw_policy` — 英国 PSW 政策
- `application_timeline` — 申请时间线常识
- `scholarship_guide` — 奖学金指南
- `top10_cs_programs_us` — 美国 CS Top10 项目精解

无需修改 Agent 代码，即可让系统在对应场景"自动具备领域专家能力"。
