"""Teacher & TeacherSchedule 访问。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


def _to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


class TeacherRepository:
    def __init__(self, engine=None):
        from src.db.engine import get_engine
        self._engine = engine or get_engine()

    def _s(self):
        return sessionmaker(bind=self._engine)()

    def get(self, teacher_id: int) -> dict | None:
        with self._s() as s:
            from src.db.models import Teacher
            row = s.get(Teacher, teacher_id)
            return _to_dict(row) if row else None

    def list_all(self) -> list[dict]:
        with self._s() as s:
            from src.db.models import Teacher
            return [_to_dict(r) for r in s.query(Teacher).all()]

    def search_by_name(self, kw: str, limit: int = 5) -> list[dict]:
        """按 name 模糊匹配老师（支持指定老师直达预约）。"""
        from src.db.models import Teacher
        if not kw:
            return []
        kw = kw.strip()
        with self._s() as s:
            rows = s.query(Teacher).filter(Teacher.name.like(f"%{kw}%")).limit(limit).all()
            return [_to_dict(r) for r in rows]

    def search_by_preferences(self, preferences: dict, limit: int = 10) -> list[dict]:
        conditions = ["1=1"]
        params: dict = {}
        gender = preferences.get("gender")
        if gender and gender != "any":
            conditions.append("gender = :gender")
            params["gender"] = gender
        for field in ("expertise_regions", "expertise_majors"):
            val = preferences.get(field)
            if val:
                conditions.append(f"{field} LIKE :f_{field}")
                params[f"f_{field}"] = f"%{val}%"
        params["limit"] = limit
        sql = text(f"SELECT * FROM teachers WHERE {' AND '.join(conditions)} LIMIT :limit")
        with self._s() as s:
            rows = s.execute(sql, params).mappings().fetchall()
        return [dict(r) for r in rows]

    def bulk_insert(self, records: list[dict]) -> int:
        from src.db.models import Teacher
        with self._s() as s:
            for r in records:
                s.add(Teacher(**{k: v for k, v in r.items() if k != "id"}))
            s.commit()
        return len(records)

    def create(self, data: dict) -> int:
        """新增一位老师，返回新 ID。"""
        from src.db.models import Teacher
        allowed = {"name", "gender", "bio", "study_abroad", "work_experience",
                   "expertise_regions", "expertise_majors", "avatar_url", "rating"}
        payload = {k: v for k, v in data.items() if k in allowed and v not in (None, "")}
        if not payload.get("name") or not payload.get("gender"):
            raise ValueError("name 与 gender 为必填")
        if payload["gender"] not in ("male", "female", "other"):
            raise ValueError("gender 必须为 male/female/other")
        with self._s() as s:
            t = Teacher(**payload)
            s.add(t)
            s.commit()
            s.refresh(t)
            new_id = t.id
        self._sync_to_json()
        return new_id

    def update(self, teacher_id: int, data: dict) -> bool:
        """更新老师信息。"""
        from src.db.models import Teacher
        allowed = {"name", "gender", "bio", "study_abroad", "work_experience",
                   "expertise_regions", "expertise_majors", "avatar_url", "rating"}
        with self._s() as s:
            t = s.get(Teacher, teacher_id)
            if t is None:
                return False
            for k, v in data.items():
                if k in allowed:
                    setattr(t, k, v if v != "" else None)
            s.commit()
        self._sync_to_json()
        return True

    def delete(self, teacher_id: int) -> bool:
        from src.db.models import Teacher
        with self._s() as s:
            t = s.get(Teacher, teacher_id)
            if t is None:
                return False
            # 级联删除关联的时段与预约（SQLite NOT NULL 外键约束）
            s.execute(text("DELETE FROM appointments WHERE teacher_id=:tid"), {"tid": teacher_id})
            s.execute(text("DELETE FROM teacher_schedule WHERE teacher_id=:tid"), {"tid": teacher_id})
            s.delete(t)
            s.commit()
        self._sync_to_json()
        return True

    def _sync_to_json(self) -> None:
        """把当前 SQLite 全表 dump 到 data/seed/teachers.json。
        Why: 让前端 CRUD 改动在重启后仍保留（init_db.py 会从 JSON 重新导入）。
        """
        import json
        from pathlib import Path
        all_t = self.list_all()
        # 按 init_db.py 的导入逻辑，保持字段顺序与原 seed 一致
        FIELDS = ("id", "name", "gender", "bio", "study_abroad", "work_experience",
                  "expertise_regions", "expertise_majors", "avatar_url", "rating")
        records = [{k: t.get(k) for k in FIELDS} for t in all_t]
        path = Path(__file__).resolve().parents[3] / "data" / "seed" / "teachers.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[teacher_repo] sync_to_json failed: {e}")


class TeacherScheduleRepository:
    def __init__(self, engine=None):
        from src.db.engine import get_engine
        self._engine = engine or get_engine()

    def _s(self):
        return sessionmaker(bind=self._engine)()

    def list_available(self, teacher_id: int, limit: int = 5) -> list[dict]:
        sql = text(
            "SELECT * FROM teacher_schedule WHERE teacher_id=:tid AND status='available' "
            "ORDER BY date, time_slot LIMIT :limit"
        )
        with self._s() as s:
            rows = s.execute(sql, {"tid": teacher_id, "limit": limit}).mappings().fetchall()
        return [dict(r) for r in rows]

    def mark_booked(self, schedule_id: int) -> None:
        with self._s() as s:
            s.execute(text("UPDATE teacher_schedule SET status='booked' WHERE id=:sid"),
                      {"sid": schedule_id})
            s.commit()

    def set_status(self, schedule_id: int, status: str) -> bool:
        if status not in ("available", "booked", "blocked"):
            raise ValueError("status 必须为 available/booked/blocked")
        with self._s() as s:
            r = s.execute(text("UPDATE teacher_schedule SET status=:st WHERE id=:sid"),
                          {"st": status, "sid": schedule_id})
            s.commit()
            return r.rowcount > 0

    def add_slot(self, teacher_id: int, date: str, time_slot: str,
                 status: str = "available") -> int:
        """添加一个时段。查重通过则插入并返回 ID，重复返回 -1。"""
        from src.db.models import TeacherSchedule
        with self._s() as s:
            dup = s.execute(
                text("SELECT id FROM teacher_schedule WHERE teacher_id=:tid AND date=:d AND time_slot=:t"),
                {"tid": teacher_id, "d": date, "t": time_slot}
            ).first()
            if dup:
                return -1
            ts = TeacherSchedule(teacher_id=teacher_id, date=date,
                                 time_slot=time_slot, status=status)
            s.add(ts)
            s.commit()
            s.refresh(ts)
            return ts.id

    def get_slot(self, schedule_id: int) -> dict | None:
        from src.db.models import TeacherSchedule
        with self._s() as s:
            r = s.get(TeacherSchedule, schedule_id)
            return _to_dict(r) if r else None

    def list_distinct_dates(self) -> list[str]:
        """返回数据库中所有非空日期的升序列表，给前端日期切换器用。"""
        with self._s() as s:
            rows = s.execute(text(
                "SELECT DISTINCT date FROM teacher_schedule WHERE date IS NOT NULL ORDER BY date"
            )).fetchall()
        return [r[0] for r in rows]

    def list_by_date(self, date: str) -> list[dict]:
        """返回指定日期的所有时段，按 teacher_id, time_slot 升序。"""
        with self._s() as s:
            rows = s.execute(text(
                "SELECT * FROM teacher_schedule WHERE date=:d ORDER BY teacher_id, time_slot"
            ), {"d": date}).mappings().fetchall()
        return [dict(r) for r in rows]

    def bulk_insert(self, records: list[dict]) -> int:
        from src.db.models import TeacherSchedule
        with self._s() as s:
            for r in records:
                s.add(TeacherSchedule(**{k: v for k, v in r.items() if k != "id"}))
            s.commit()
        return len(records)

