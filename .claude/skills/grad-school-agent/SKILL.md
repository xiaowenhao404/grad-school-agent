---
name: grad-school-agent
description: "Grad-School-Agent 项目的 Agent prompt 调试与 LangGraph 路由测试。帮助渲染 prompt 模板、跑单个 Agent 隔离测试、验证 TaskClassifier 分类准确率、查看 GraphState 流转。Use when user says '调试 agent', '改 prompt', 'classifier 分类不对', '测一下 agent', 'debug langgraph', '看 state'."
---

# Grad-School-Agent — Agent 与编排调试

帮助用户调试 5 个核心 Agent 与 LangGraph supervisor（详见 [`DEV_SPEC.md` 第 6 章](../../../DEV_SPEC.md#6-agent-详细设计)）。

## 调试场景

| 用户问题 | 本 skill 提供的工作流 |
|---------|---------------------|
| "Classifier 把咨询误判成预约" | 拉出 prompt → 加 few-shot 例子 → 跑分类测试集 |
| "AppointmentAgent 状态机卡在 collect_preferences" | 打印 state.appointment_slots → 看哪个字段缺 |
| "想改 ConsultantAgent 的回复风格" | 编辑 `config/prompts/consultant.txt` → 跑测试 query |
| "pre-hook 没注入 user_profile" | 检查 memory_enabled + UserRepository.get_profile 调用链 |
| "Conditional edge 路由错了" | 在 supervisor.py 加 print；或单独跑 route_by_task_type 函数 |

## 工作流

### 1. 准备

读：

- [`src/graph/supervisor.py`](../../../src/graph/supervisor.py) — 顶层编排
- [`src/graph/state.py`](../../../src/graph/state.py) — GraphState 字段
- [`src/graph/hooks.py`](../../../src/graph/hooks.py) — pre/post hook
- [`src/agents/`](../../../src/agents/) — 5 个 Agent
- [`config/prompts/`](../../../config/prompts/) — 全部 prompt 模板

### 2. 隔离测试单个 Agent

```python
from src.graph.state import GraphState
from src.agents.task_classifier import TaskClassifier

state: GraphState = {
    "user_id": 1,
    "conversation_id": 1,
    "user_input": "我想了解美国 CS Top10 学校",
    "user_profile": {},
    "memory_enabled": True,
    "messages": [],
}
out = TaskClassifier().run(state)
print("task_type:", out["task_type"])
```

### 3. 验证分类准确率

准备一个 csv（10-20 条）：

```
user_input,expected_task_type
我想预约老师,appointment
帮我看下学费,school
今天天气,reject
...
```

跑批量分类，输出混淆矩阵。

### 4. 跑完整 supervisor 端到端

```python
from src.graph.supervisor import build_supervisor_graph

graph = build_supervisor_graph()
result = graph.invoke({"user_id": 1, "user_input": "..."})
print("Final state:", result)
```

### 5. Prompt 改进套路

1. 拉出当前模板（`config/prompts/<agent>.txt`）
2. 找到失败 case：哪个字段渲染错了？缺哪个 placeholder？
3. 改 prompt：增加 few-shot / 加强约束 / 输出格式化要求
4. 跑 10 条 sanity test 不回归
5. 提交（用 `git-commit-conventions` skill）

## 注意

- 改 prompt 时确保 placeholder（如 `{user_profile}`）和 Agent 实际渲染的 dict 一致
- LangGraph 调试时优先用同步 `.invoke()`，异步留到稳定后
- 不要把 system prompt 写死在 Python 代码里 → 一律走 `config/prompts/`
