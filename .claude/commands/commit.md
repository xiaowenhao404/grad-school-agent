---
description: 按 Conventional Commits 规范提交所有 staged 改动。type 限定为 feat/fix/docs/style/refactor/test/chore/perf。
allowed-tools: Bash
---

# /commit — 按 Conventional Commits 规范提交

依据：`.claude/skills/git-commit-conventions/SKILL.md`。本命令是该 skill 的"动作版"。

## 执行步骤

1. **查看状态**：跑 `git status --short` 看哪些文件待提交
2. **若用户指明范围**则 `git add <范围>`；否则若已有 staged 改动直接走，否则提醒用户先 `git add`
3. **看 diff**：跑 `git diff --staged --stat` 与 `git diff --staged | head -200` 了解改动
4. **判 type**：参照下表（必须从 8 种里选一个，**全小写**）
5. **生成 message**：格式 `<type>: <中文一行说明>` + （可选多行 body 解释 why）
6. **提交**（用 heredoc 保留中文换行）：
   ```bash
   git commit -m "$(cat <<'EOF'
   <type>: <说明>

   <可选 body>
   EOF
   )"
   ```
7. **确认**：跑 `git log -1 --oneline`

## Type 选择表（8 种）

| Type | 用途 | 例 |
|---|---|---|
| `feat` | 新增功能 | `feat: 新增 /commit slash command` |
| `fix` | 修 bug | `fix: 修复 appointment 状态机跨轮丢失` |
| `docs` | 仅文档/注释 | `docs: 补充 README 启动说明` |
| `style` | 不影响语义的格式 | `style: 统一 prompt 文件缩进` |
| `refactor` | 重构（非新增非修复） | `refactor: 拆分 ChatService` |
| `test` | 加/改测试 | `test: 加 appointment 状态机单测` |
| `chore` | 构建/工具/依赖 | `chore: 升级 marked 到 v12` |
| `perf` | 性能优化 | `perf: 老师列表加索引` |

## 写好 commit 的额外约束

- **中文 body 描述「为什么」**，不重复 diff 显示的"什么"
- **不要混合 feat 和 fix**（拆 2 个 commit）
- **专业名词保留英文**（如 SSE、CRUD、Markdown）
- **绝不**：
  - `--no-verify`（除非用户明确说跳过 hook）
  - 改 git config
  - 主动 push（push 应由 `/push` 或用户明示）
  - 用 `git add .` / `git add -A` —— 应该用具体文件路径，避免误提交 secrets

## 示例输出

```text
✅ 已提交：a3f5c2d feat: 修复多轮预约状态机跨轮丢失，新增 conversation_state 表
   3 files changed, 87 insertions(+), 12 deletions(-)
```
