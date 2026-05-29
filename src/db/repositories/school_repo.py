"""School & SchoolProgram 访问。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


def _to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


class SchoolRepository:
    def __init__(self, engine=None):
        from src.db.engine import get_engine
        self._engine = engine or get_engine()

    def _s(self):
        return sessionmaker(bind=self._engine)()

    def get(self, school_id: int) -> dict | None:
        with self._s() as s:
            from src.db.models import School
            row = s.get(School, school_id)
            return _to_dict(row) if row else None

    def list_all(self) -> list[dict]:
        with self._s() as s:
            from src.db.models import School
            return [_to_dict(r) for r in s.query(School).all()]

    def bulk_insert(self, records: list[dict]) -> int:
        from src.db.models import School
        with self._s() as s:
            for r in records:
                s.add(School(**{k: v for k, v in r.items() if k != "id"}))
            s.commit()
        return len(records)


class SchoolProgramRepository:
    def __init__(self, engine=None):
        from src.db.engine import get_engine
        self._engine = engine or get_engine()

    def _s(self):
        return sessionmaker(bind=self._engine)()

    def get(self, program_id: int) -> dict | None:
        with self._s() as s:
            from src.db.models import SchoolProgram
            row = s.get(SchoolProgram, program_id)
            return _to_dict(row) if row else None

    def filter_programs(self, preferences: dict, limit: int = 50) -> list[int]:
        conditions = ["1=1"]
        params: dict = {}
        tr = preferences.get("tuition_range")
        if tr and len(tr) == 2:
            conditions.append("p.tuition_per_year BETWEEN :t_min AND :t_max")
            params["t_min"], params["t_max"] = tr
        qr = preferences.get("qs_rank_range")
        if qr and len(qr) == 2:
            conditions.append("(s.qs_rank IS NULL OR s.qs_rank BETWEEN :q_min AND :q_max)")
            params["q_min"], params["q_max"] = qr
        country = preferences.get("country")
        if country:
            conditions.append("s.country = :country")
            params["country"] = country
        major = preferences.get("major_category")
        if major:
            conditions.append("p.major_category = :major")
            params["major"] = major
        dur = preferences.get("duration_max")
        if dur:
            conditions.append("p.duration_months <= :dur")
            params["dur"] = dur
        lang = preferences.get("language_score", {})
        if lang.get("ielts"):
            conditions.append("(p.ielts_min IS NULL OR p.ielts_min <= :ielts)")
            params["ielts"] = lang["ielts"]
        if lang.get("toefl"):
            conditions.append("(p.toefl_min IS NULL OR p.toefl_min <= :toefl)")
            params["toefl"] = lang["toefl"]
        params["limit"] = limit
        sql = text(
            f"SELECT p.id FROM school_programs p JOIN schools s ON p.school_id=s.id "
            f"WHERE {' AND '.join(conditions)} ORDER BY s.qs_rank LIMIT :limit"
        )
        with self._s() as s:
            rows = s.execute(sql, params).fetchall()
        return [r[0] for r in rows]

    def get_program_with_school(self, program_id: int) -> dict | None:
        sql = text(
            "SELECT p.*, s.names, s.country, s.country_en, s.qs_rank, s.official_site "
            "FROM school_programs p JOIN schools s ON p.school_id=s.id WHERE p.id=:pid"
        )
        with self._s() as s:
            row = s.execute(sql, {"pid": program_id}).mappings().first()
        return dict(row) if row else None

    def bulk_insert(self, records: list[dict]) -> int:
        from src.db.models import SchoolProgram
        with self._s() as s:
            for r in records:
                s.add(SchoolProgram(**{k: v for k, v in r.items() if k != "id"}))
            s.commit()
        return len(records)
