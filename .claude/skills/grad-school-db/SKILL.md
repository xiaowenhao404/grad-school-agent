---
name: grad-school-db
description: "Grad-School-Agent 项目的 SQLite schema 设计、迁移与文档同步。帮助加字段、改表、生成 Alembic migration、自动更新 docs/DB_SCHEMA.md。强制纪律：schema 改动必须同步 ORM comment 与 DB_SCHEMA.md。Use when user says '改 schema', '加字段', '改数据库', 'migration', 'alembic', '加表', '改 ORM'."
---

# Grad-School-DB — Schema 维护

帮助用户改动 SQLite schema，**强制保证 ORM 注释、`docs/DB_SCHEMA.md` 同步**（详见 [`DEV_SPEC.md` 附录 A](../../../DEV_SPEC.md#附录-a数据库-schema-同步规范)）。

## 三件套同步纪律

任何 schema 变更必须**同一次提交**完成三件事：

1. **改 ORM**（[`src/db/models.py`](../../../src/db/models.py)）— 字段加 `comment=`
2. **改 Repository**（[`src/db/repositories/`](../../../src/db/repositories/)）— 适配新字段
3. **改文档**（[`docs/DB_SCHEMA.md`](../../../docs/DB_SCHEMA.md)）— 同步字段表

缺其一视为未完成。

## 工作流

### 场景 A：加字段

例：给 `teachers` 表加 `email` 字段。

1. **改 ORM**：

```python
# src/db/models.py
class Teacher(Base):
    ...
    email = Column(
        String(128),
        nullable=True,
        comment="联系邮箱（可空，用于预约成功后通知老师）",
    )
```

2. **生成 migration**：

```powershell
uv run alembic revision --autogenerate -m "feat(db): teachers 加 email 字段"
uv run alembic upgrade head
```

3. **改 Repository**：在 `teacher_repo.py` 的 `upsert` / `get` 中处理 email。

4. **改 DB_SCHEMA.md**：在 `teachers` 表的字段表加一行。

5. **跑回归**：`uv run pytest tests/unit/test_teacher_repo.py`

6. **提交**：`feat(db): teachers 加 email 字段（含 migration + 文档同步）`

### 场景 B：加新表

参考 `schools` / `school_programs` 拆分模式：

1. ORM 加新 class，所有字段写 comment
2. ORM `__table_args__ = {"comment": "..."}`
3. 加 repository
4. 写 migration
5. 在 DB_SCHEMA.md 加整张表

### 场景 C：从 ORM 生成 schema 文档

```python
from src.db.models import Base

for table in Base.metadata.tables.values():
    print(f"## {table.name}\n{table.comment or ''}\n")
    for col in table.columns:
        print(f"- `{col.name}` ({col.type}) — {col.comment or ''}")
```

把输出贴到 `docs/DB_SCHEMA.md` 对应表的"字段表"小节。

## 反模式（拦截）

- ❌ 用 raw SQL 改 schema（绕过 ORM） → 必须改 ORM
- ❌ 改 ORM 但不写 migration → 用户拉新代码后跑不起来
- ❌ 改 ORM 但不更新 DB_SCHEMA.md → 文档与代码脱钩，团队踩坑
- ❌ 字段不写 comment → 半年后没人记得这字段干嘛
