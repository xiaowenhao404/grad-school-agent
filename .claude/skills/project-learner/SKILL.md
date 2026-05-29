---
name: project-learner
description: "Grad-School-Agent 项目知识点学习/复习教练。读取 DEV_SPEC.md 与源码骨架，按模块（LangGraph 多 Agent / Hybrid RAG / SQLite 数据模型 / Streamlit 前端 / Runtime Skills 插件）出题、追问、评分、给参考答案。Use when user says '学习项目', '复习项目', '项目知识点打卡', '考我知识点', 'knowledge check'。"
---

# Project Learner — Grad-School-Agent

帮助用户系统掌握本项目的核心知识点。所有学习与提问都以 [`DEV_SPEC.md`](../../../DEV_SPEC.md) 与源码骨架为锚点，不引入项目外的虚构内容。

## 准备工作

开始前先读：

1. [`DEV_SPEC.md`](../../../DEV_SPEC.md) — 完整设计规范
2. [`README.md`](../../../README.md) — 项目入口与目录
3. 相关模块骨架（按用户选择的领域）：
   - `src/agents/` — 多 Agent 实现
   - `src/graph/` — LangGraph 编排
   - `src/rag/` — Hybrid RAG
   - `src/db/models.py` — 数据模型
   - `src/runtime_skills/` — 运行时 skill 插件

## 学习模式

询问用户：

| 模式 | 行为 |
|------|------|
| 学习新知识点 | 选一个未学/薄弱模块，从概念→源码→应用三层讲解 |
| 复习薄弱知识点 | 出题考核，给评分与参考答案 |
| 项目讲解练习 | 让用户用 3-5 分钟讲一个模块，纠正不准确的表述 |

## 知识域

按 DEV_SPEC.md 的章节组织：

| 域 | 关键概念 | 源码锚点 |
|------|---------|---------|
| **LangGraph 多 Agent** | StateGraph / Node / Conditional Edge / Subgraph / Pre-Post hook | `src/graph/supervisor.py`、`src/graph/hooks.py`、`src/agents/*.py` |
| **Hybrid RAG** | BM25 / Dense / RRF / 两段式检索 | `src/rag/retrieval/hybrid_search.py`、`src/rag/retrieval/dense_retriever.py` |
| **数据模型** | 7 表 ER / schools-programs 拆分 / SQLAlchemy comment | `src/db/models.py` |
| **Runtime Skills** | 插件接口 / 自动发现 / 注入 prompt | `src/runtime_skills/base.py`、`src/runtime_skills/registry.py` |
| **多轮状态机** | 预约状态机 / GraphState | `src/agents/appointment_agent.py`、`DEV_SPEC.md 4.4.3` |
| **DeepSeek 集成** | OpenAI 兼容 SDK / function calling | `src/llm/deepseek_client.py`、`src/tools/registry.py` |

## 出题原则

- 每次提问紧扣一个明确知识点；不出"开放式空泛题"
- 用户答完后给评分（1-5 分）+ 关键漏点 + 参考答案
- 参考答案必须引用源码位置（如 `src/rag/retrieval/hybrid_search.py` 的 `_rrf_fuse`）
