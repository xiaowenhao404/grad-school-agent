"""Appointment 访问。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


class AppointmentRepository:
    def __init__(self, engine=None):
        from src.db.engine import get_engine
        self._engine = engine or get_engine()

    def _s(self):
        return sessionmaker(bind=self._engine)()

    def create(self, user_id: int, teacher_id: int, schedule_id: int,
               topic: str | None = None) -> int:
        from src.db.models import Appointment, TeacherSchedule
        with self._s() as s:
            slot = s.get(TeacherSchedule, schedule_id)
            if slot is None or slot.status != "available":
                raise ValueError(f"schedule_id={schedule_id} not available")
            slot.status = "booked"
            appt = Appointment(user_id=user_id, teacher_id=teacher_id,
                               schedule_id=schedule_id, topic=topic, status="confirmed")
            s.add(appt)
            s.commit()
            s.refresh(appt)
            return appt.id

    def list_by_user(self, user_id: int) -> list[dict]:
        sql = text("SELECT * FROM appointments WHERE user_id=:uid ORDER BY created_at DESC")
        with self._s() as s:
            rows = s.execute(sql, {"uid": user_id}).mappings().fetchall()
        return [dict(r) for r in rows]

    def cancel(self, appointment_id: int) -> None:
        from src.db.models import Appointment, TeacherSchedule
        with self._s() as s:
            appt = s.get(Appointment, appointment_id)
            if appt:
                appt.status = "cancelled"
                slot = s.get(TeacherSchedule, appt.schedule_id)
                if slot:
                    slot.status = "available"
                s.commit()

