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

    def bulk_insert(self, records: list[dict]) -> int:
        from src.db.models import TeacherSchedule
        with self._s() as s:
            for r in records:
                s.add(TeacherSchedule(**{k: v for k, v in r.items() if k != "id"}))
            s.commit()
        return len(records)

