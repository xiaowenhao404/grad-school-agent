# Grad-School-Agent

> **申研选校预约系统** — 自然语言处理课程项目
>
> 多 Agent 协作 + Hybrid RAG + Streamlit 前端

## 项目简介

面向出国申研场景的对话式智能助手，背后由多个分工明确的 Agent 协作：

- **咨询机器人**：回答签证指南、公司介绍、服务说明等通用问题
- **选校机器人**：根据偏好（学费 / QS / 国家 / 专业 / 语言要求）匹配学校项目
- **预约机器人**：根据偏好匹配咨询老师，查询时间，完成预约
- **行为分析**：可开关的偏好记忆，自动用于个性化推荐

详细设计见 [`DEV_SPEC.md`](DEV_SPEC.md)。

## 技术栈

| 类别 | 选型 |
|------|------|
| Agent 编排 | LangGraph |
| LLM | DeepSeek API（兼容 OpenAI SDK） |
| RAG | Chroma + BM25 + RRF 混合检索 |
| 数据库 | SQLite + SQLAlchemy |
| 前端 | Streamlit 多页面 |
| 包管理 | uv |

## 快速开始

```bash
# 1. 安装依赖（推荐 uv）
uv sync

# 2. 配置环境变量
cp .env.example .env  # Windows: copy .env.example .env
# 编辑 .env 填入 DeepSeek API key

# 3. 初始化数据库与 seed 数据
uv run python -m src.db.init_db

# 4. 启动 Streamlit
uv run streamlit run app.py
```

或参考 `.claude/skills/setup-environment` 一键配置。

## 目录结构

详见 [`DEV_SPEC.md` 第 4.2 节](DEV_SPEC.md#42-目录结构)。核心：

```
src/
├── agents/         # 5 个核心 Agent
├── graph/          # LangGraph 编排
├── rag/            # Hybrid RAG 流水线
├── tools/          # LangChain Tools（预留 MCP 接入）
├── runtime_skills/ # 运行时领域 skill 插件（项目亮点）
├── db/             # SQLite + Repositories
├── services/       # 业务服务层
└── llm/            # DeepSeek / Embedding 客户端

ui/                 # Streamlit 5 个页面
.claude/skills/     # Claude Code 开发期辅助 skill
```

## 仓库信息

- 远程仓库：<https://github.com/xiaowenhao404/Grad-School-Agent>
- 默认分支：`main`

## 开发规范

### Git 提交规范

本项目采用 **Conventional Commits** 规范，提交消息格式：

```text
<type>: <中文说明>
```

| Type | 说明 |
| :--- | :--- |
| `feat` | 新增功能（Feature） |
| `fix` | 修复 Bug |
| `docs` | 仅包含文档的修改（Documentation） |
| `style` | 不影响代码含义的修改（空格、格式化、缺少分号等） |
| `refactor` | 代码重构（既不新增功能，也不修复 Bug） |
| `test` | 添加缺失的测试或修正现有测试 |
| `chore` | 对构建过程或辅助工具和库的更改 |
| `perf` | 提高性能的代码更改（Performance） |

说明文字使用中文，专业名词保持英文。详见 [.claude/skills/git-commit-conventions/SKILL.md](.claude/skills/git-commit-conventions/SKILL.md)。

## 目录约定

- `/plan` — 计划文档
- `/temp` — 临时文件（已在 `.gitignore` 中排除）
- `/docs/superpowers/specs/` — brainstorming 设计文档
