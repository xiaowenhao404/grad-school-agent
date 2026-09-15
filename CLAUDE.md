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

- 包管理：**uv**（依赖见 `pyproject.toml`；已设 `[tool.uv] package = false`，避免中文路径下生成 .pth 触发 GBK 解码崩溃）
- Python 解释器：`.venv\Scripts\python.exe`（`uv sync` 自动创建，CPython 3.11.9）
- Web 服务器：**Waitress**（不要用 Flask dev server，Windows 上有 SSE/socket bug）
- 启动：`.venv\Scripts\python.exe app.py`（或 `python -m uv run python app.py`）
- 重建环境：`python -m uv sync`（依赖变更后；从缓存装很快）
- 数据库：`data/grad_school.db`（SQLite）
- 向量库：`data/chroma/`（含 3 个 collection：schools / teachers / internal_docs）
- Embedding：本地 BGE `./models/bge-small-zh-v1.5`（offline，零成本）
- LLM 配置：`.env`（Claude proxy + UA header；`base_url=https://daodunapi.com/v1`，模型 `claude-opus-4-8`）

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
- **新外部工具**：写在 `src/tools/<name>_tool.py` 并 `registry.register(fn)`，再在 `src/tools/registry.py` 的 `_TOOL_SCHEMAS` 补 JSON Schema —— **只需这一步**，进程内调用与标准 MCP Server 会同时暴露它（`src/mcp_server/server.py` 从 `registry.list_tools()` 动态构建，不要在 MCP 层再写一份实现）

---

## 工具层的两条暴露路径

同一份工具实现（`src/tools/*_tool.py`）对外有两条路径，改动时两边都要顾及：

1. **进程内 `ToolRegistry`**（`src/tools/registry.py`）：Agent 在 Flask 进程里直接 `registry.call_tool(...)`；另有 `GET /api/mcp/tools`、`POST /api/mcp/call/<name>` 两个 HTTP 端点便于调试。**这是 Agent 在用的路径，改动要保持向后兼容。**
2. **标准 MCP Server**（`src/mcp_server/`）：基于官方 `mcp` Python SDK（2.x，v1 的 `FastMCP` 已更名为 `MCPServer`），JSON-RPC over stdio，供 Claude Desktop / Cursor / MCP Inspector 等外部 MCP Client 接入。

启动：`uv run python -m src.mcp_server`（stdout 被 JSON-RPC 帧独占，**任何日志必须走 stderr**，一条 `print()` 就会破坏协议帧）。

验证：`uv run --extra dev pytest tests/unit/test_mcp_server.py tests/integration/test_mcp_stdio.py`
（后者会真的起子进程走完 initialize / tools/list / tools/call）。

---

## 验证 plan

每次重要改动后：

```powershell
.venv\Scripts\python.exe app.py
# 浏览器开 http://127.0.0.1:5000 实测影响的功能
```
