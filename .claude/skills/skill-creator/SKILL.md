---
name: skill-creator
description: Guide for creating new Claude Code skills inside the Grad-School-Agent project. Distinguishes between `.claude/skills/` (Claude Code dev-helper skills) and `src/runtime_skills/` (system runtime skills called by Agents). Use when user says "create skill", "new skill", "build a skill", "添加 skill", "新建 skill".
---

# Skill Creator — Grad-School-Agent

帮助用户在本项目内创建新 skill。**第一步必须确认 skill 类型**，因为本项目有两类完全不同位置/用途的 skill。

## 两类 Skill 的区别

| 维度 | `.claude/skills/` | `src/runtime_skills/` |
|------|-------------------|----------------------|
| 服务对象 | Claude Code（开发期） | 系统 Agent（运行时） |
| 是否随系统运行 | 否 | 是 |
| 触发方式 | 用户在 Claude Code 对话时被自动加载 | Agent 通过 SkillRegistry 调用 |
| 格式 | YAML frontmatter + Markdown body | Python `BaseRuntimeSkill` 实现 |
| 示例 | setup-environment, grad-school-rag | us_visa_knowledge |

**开门第一问**："你想创建的是开发期辅助 skill（帮 Claude Code 做开发），还是运行时领域 skill（让 Agent 在对话中具备某个领域专家能力）？"

## 路径 A：创建 `.claude/skills/` skill

### 文件结构

```
.claude/skills/{kebab-case-name}/
├── SKILL.md            ← 必须，含 frontmatter + body
├── references/         ← 可选，存放被 SKILL.md 引用的资料
└── scripts/            ← 可选，存放辅助脚本
```

### SKILL.md 模板

```markdown
---
name: skill-name-here
description: "一句话说明做什么 + 触发词（如 Use when user says '...'）"
---

# Skill Title

## 准备
（开始前需要读哪些文件）

## 工作流程
（多步流程列表，每步可执行）

## 注意事项
（边界、降级、错误处理）
```

### 质量准则

- **简洁优先**：context 是公共资源。不写 Claude 已经知道的废话。
- **触发词明确**：description 末尾必须含 `Use when user says "...", "..."` 以提高匹配率。
- **可执行**：步骤要让 Claude 能直接照做，不写空泛建议。

## 路径 B：创建 `src/runtime_skills/` skill

### 文件结构

```
src/runtime_skills/{snake_case_name}/
├── __init__.py         ← 必须，实现 BaseRuntimeSkill 并 register
└── data/               ← 可选，本 skill 用的知识资料（如 .md/.json）
```

### `__init__.py` 模板

```python
from src.runtime_skills.base import BaseRuntimeSkill
from src.runtime_skills.registry import skill_registry


class MyDomainSkill(BaseRuntimeSkill):
    name = "my_domain"
    description = "提供 XX 领域的常识 / 规则 / 数据"

    def match(self, query: str, context: dict) -> bool:
        # 决定本 skill 是否在当前查询下被启用
        return "关键词" in query

    def provide_context(self, query: str, context: dict) -> str:
        # 返回要注入到 prompt 的 markdown 文本
        return "..."


skill_registry.register(MyDomainSkill())
```

### 质量准则

- **match 要精确**：避免误命中导致 prompt 噪音
- **provide_context 要简短**：注入的文本进入每次 LLM 调用，控制 token 成本
- **失败安全**：内部异常不能影响 Agent 主流程（Registry 已有 try/except 兜底，但 skill 自己也要鲁棒）
- **数据外置**：知识资料放在 `data/` 子目录或 `data/raw_docs/`，按需加载

## 注册 / 启用

- `.claude/skills/`：放好 SKILL.md 即生效（Claude Code 启动时自动扫描）
- `src/runtime_skills/`：放好 `__init__.py` 后调用 `skill_registry.discover()` 即生效（启动入口需调一次）

详见 [`src/runtime_skills/README.md`](../../../src/runtime_skills/README.md)。
