---
name: grad-school-eval
description: "Grad-School-Agent 项目的对话效果评估。提供 golden test set 模板、LLM-as-judge 评估脚本骨架、关键场景的人工评分表。Use when user says '评估对话', '看下效果', 'evaluate', 'golden set', '回归测试 agent', '效果回归'."
---

# Grad-School-Eval — 对话效果评估

帮助用户系统化评估 Grad-School-Agent 各 Agent 与端到端对话质量。本项目**不做自动化 RAG 评估闭环**（见 [`DEV_SPEC.md` 第 8 章](../../../DEV_SPEC.md#8-测试方案)），但保留这套半人工评估流程作为回归手段。

## 评估对象

| 对象 | 关键指标 |
|------|---------|
| **TaskClassifier** | 分类准确率（confusion matrix） |
| **ConsultantAgent** | 回答相关性、引用准确性（Hit Rate@K） |
| **SchoolSelectionAgent** | 偏好提取准确性、Top3 项目符合约束的比例 |
| **AppointmentAgent** | 状态机推进正确性、预约成功率 |
| **UserBehavior post-hook** | 偏好提取 JSON 与人工标注的字段重合度 |
| **端到端** | 主观满意度（5 分制）、平均轮数到达成目标 |

## Golden Test Set 结构

放在 `tests/fixtures/golden_set.json`：

```json
[
  {
    "id": "consult_001",
    "scenario": "签证咨询",
    "user_inputs": ["F1 签证需要准备什么？"],
    "expected_task_type": "consultant",
    "expected_sources": ["us_visa_guide.pdf"],
    "expected_keywords": ["I-20", "DS-160", "SEVIS"]
  },
  {
    "id": "school_001",
    "scenario": "选校（学费区间）",
    "user_inputs": [
      "我想去美国读 CS 硕士",
      "学费不超过 12 万美元",
      "QS 前 50 即可"
    ],
    "expected_task_type": "school",
    "expected_program_constraints": {
      "country": "美国",
      "major_category": "CS",
      "tuition_max_usd": 120000,
      "qs_max": 50
    },
    "min_results": 1,
    "max_results": 3
  }
]
```

## 评估工作流

### 1. 准备 golden set（半人工）

- 课程项目阶段：10-20 条覆盖每个 Agent + 拒绝场景
- 让用户审核每条 expected 输出

### 2. 跑分类批测

```python
import json
from src.agents.task_classifier import TaskClassifier

cases = json.load(open("tests/fixtures/golden_set.json"))
classifier = TaskClassifier()

correct = 0
for c in cases:
    state = {"user_input": c["user_inputs"][0], ...}
    out = classifier.run(state)
    if out["task_type"] == c["expected_task_type"]:
        correct += 1
    else:
        print(f"FAIL {c['id']}: expected={c['expected_task_type']} got={out['task_type']}")

print(f"Accuracy: {correct}/{len(cases)} = {correct/len(cases):.2%}")
```

### 3. LLM-as-judge（咨询/选校等开放回答）

用 DeepSeek 当"裁判"：

```
你是一个评估助手。下面是用户问题、参考答案要点、系统回答。请按以下 4 项 1-5 分打分：
- 相关性（回答是否切题）
- 准确性（事实是否正确）
- 完整性（是否覆盖参考要点）
- 引用规范（是否给出来源标注）

问题：{question}
参考要点：{expected_keywords}
系统回答：{actual_response}

只输出 JSON：{"relevance": int, "accuracy": int, "completeness": int, "citation": int}
```

### 4. 报告

输出 markdown 报告：

- 每个 Agent 的 metric 汇总表
- Top failures 列表（id + 原因）
- 改进建议（具体到 prompt 修改方向）

## 不做什么

- 不接入 Ragas / DeepEval 等正式框架（DEV_SPEC.md 明确"显式不做"）
- 不算端到端延迟性能（无 latency SLO）
- 不与"上线效果"对比（本项目无生产数据）
