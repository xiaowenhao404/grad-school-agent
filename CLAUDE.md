# Grad-School-Agent — Project Memory

> 项目专属指令；全局 Claude 配置见 `~/.claude/CLAUDE.md`。

## 项目简介

申研选校预约系统（自然语言处理课程项目）：多 Agent（LangGraph）+ Hybrid RAG（Chroma + BM25 + jieba）+ Flask + Waitress。

详细架构见 [DEV_SPEC.md](DEV_SPEC.md)。

---

## Git 工作纪律（强制）

- **每完成一个独立功能/修复后立即用 `/commit` 提交**，绝不批量囤积
- commit message 严格符合 [.claude/skills/git-commit-conventions/SKILL.md](.claude/skills/git-commit-conventions/SKILL.md) 规范
- type 限定 `feat / fix / docs / style / refactor / test / chore / perf`（8 种，全小写）
- 单次提交内容**聚焦一件事**，不混合 feat + fix（拆 2 个 commit）
- 中文 body 描述「**为什么**」而非「什么」（"什么"在 diff 里已经清楚了）
- **禁止**：`--no-verify` / `git add .` / `git add -A`（误提交 secrets 风险）/ 主动 push

---

## 开发环境

- Python：`D:\anaconda\envs\NLP-Lab\python.exe`（Anaconda 子环境）
- Web 服务器：**Waitress**（不要用 Flask dev server，Windows 上有 SSE/socket bug）
- 启动：`D:\anaconda\envs\NLP-Lab\python.exe app.py`
- 数据库：`data/grad_school.db`（SQLite）
- 向量库：`data/chroma/`（含 3 个 collection：schools / teachers / internal_docs）
- LLM 配置：`.env`（已套用 Claude proxy + UA header）

---

## 数据同步约定

- **老师 CRUD（add/update/delete）必须同步 `data/seed/teachers.json`**：`TeacherRepository._sync_to_json()` 在 create/update/delete 后自动调用
- **上传内部文档必须落盘到 `data/raw_docs/internal/`**：`/api/upload` 已实现（含时间戳前缀防重名）
- 不要把生成数据塞到 `data/seed/`，那是种子数据目录，CRUD 写回需谨慎

---

## 多轮状态机持久化

`AppointmentAgent` 是多轮状态机，必须靠 `conversation_state` 表跨 turn 持久化 `appointment_slots`。改 ChatService 时**不要忘记 `_persist_state()`**。

---

## 文件级别约定

- **Agent prompts**：`config/prompts/*.txt`，占位符用 `{xxx}` —— 用 `BaseAgent._render_prompt(**kw)` 渲染（不是 jinja2）
- **新 Repository 方法**：放 `src/db/repositories/`，所有 method 用 `with self._s() as s` 上下文管理 session
- **新 API 路由**：放 `app.py`，遵循 `/api/<resource>/<action>` 命名

---

## 验证 plan

每次重要改动后：

```powershell
D:\anaconda\envs\NLP-Lab\python.exe app.py
# 浏览器开 http://127.0.0.1:5000 实测影响的功能
```
