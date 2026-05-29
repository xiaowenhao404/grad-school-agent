---
name: resume-writer
description: "基于 Grad-School-Agent 项目生成定制化简历项目经历。结合 LangGraph 多 Agent、Hybrid RAG、Runtime Skills 插件等技术亮点，按四段式结构输出高质量中文或英文项目描述。Use when user says '写简历', '简历项目', '项目经历', 'resume', '包装项目', '优化简历', or asks to generate resume content based on this project."
---

# Resume Writer — Grad-School-Agent

基于"四段式结构 + 项目亮点 + 包装边界 + 用户画像 = 定制简历"模型，生成本项目的简历经历段落。默认中文，用户要求时输出英文。

## 工作流程

### Phase 1: 加载知识

1. [`DEV_SPEC.md`](../../../DEV_SPEC.md) — 完整技术细节与亮点
2. [`README.md`](../../../README.md) — 项目摘要

### Phase 2: 用户画像采集

一次性收集（多选 + 单选），≤4 个问题：

- **目标岗位**：Agent Engineer / LLM Application / RAG Engineer / NLP Engineer / Backend / 学术研究
- **简历风格**：技术深度 / 业务落地 / 学术成果
- **字数预算**：3-4 行精简 / 6-8 行标准 / 10+ 行详细
- **想突出的技术点**（多选）：LangGraph / Hybrid RAG / 多 Agent / 插件机制 / 数据建模 / Streamlit

### Phase 3: 四段式结构生成

每个项目经历输出：

1. **项目定位（1 行）**：一句话讲清项目是什么 + 体现技术含量
2. **技术亮点（2-4 条 bullet）**：每条用 "技术名词 + 量化效果/规模" 包装
3. **个人贡献（1-2 条 bullet）**：突出 ownership 与可量化产出
4. **使用技术栈（1 行）**：tag 化技术列表

### Phase 4: 量化锚点（项目特定）

| 数据 | 量级 | 简历用法 |
|------|------|---------|
| 老师 | 30 | "管理 30 位咨询老师档案与时间槽" |
| 学校 / 项目 | 80 / 200 | "构建 80 所学校 / 200+ 项目知识库" |
| 文档 | 20 | "摄取 20+ 份签证/服务 PDF 文档" |
| Agent 数 | 5 + 工具层 | "实现 5 个核心 Agent 协作" |
| 检索 | Hybrid (BM25+Dense+RRF) | "BM25 + Dense Embedding 混合检索，RRF 融合" |

## 包装边界（防止过度）

- **可包装**：Runtime Skills 插件机制是真实创新，可放大
- **不可虚构**：未实现的 reranker / MCP server / 评估闭环只能写"架构预留扩展点"，不可写"已实现"
- **谨慎用词**：演示数据集 → "构建中小规模知识库"；不写"千万级数据"
- **声明**：若用户简历写为线上系统，必须说明"个人课程项目，本地运行"

## 模板示例（中文，标准长度）

```
申研选校多 Agent 助手 | Personal Project | 2026
- 基于 LangGraph 设计 5 个核心 Agent（分类/咨询/选校/预约/用户行为）协作的状态图编排系统，
  以 pre-hook 注入用户画像、post-hook 异步更新偏好，实现跨轮对话的个性化推荐
- 实现 BM25 + Dense Embedding 双路召回 + RRF 融合的 Hybrid RAG 检索，覆盖 80 所学校
  / 200+ 申请项目 / 20+ 签证文档三个 Chroma collection
- 设计插件化 Runtime Skills 机制（接口 + 自动发现 + prompt 注入），新增领域知识无需修改 Agent 代码
- 设计 9 张 SQLite 表（含 schools / programs 拆分模型），以 SQL 预过滤 + Chroma 语义检索
  的两段式架构降低召回噪音
技术栈: Python · LangGraph · LangChain · Chroma · BM25 · DeepSeek · SQLAlchemy · Streamlit
```
