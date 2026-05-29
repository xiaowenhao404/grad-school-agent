"""数据访问层。

详见 DEV_SPEC.md 第 5 章数据库设计、附录 A schema 同步规范。

子模块：
- models.py: SQLAlchemy ORM（所有字段带 comment=，与 docs/DB_SCHEMA.md 同步）
- repositories/: 仓储模式，业务层只依赖 repository 不直连 ORM
- init_db.py: 建表 + 导入 seed 数据
"""
