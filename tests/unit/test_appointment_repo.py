"""单测：AppointmentRepository — 事务一致性。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, Teacher, TeacherSchedule, User, UserProfile


@pytest.fixture
def mem_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    import src.db.engine as eng_mod
    eng_mod.get_engine.cache_clear()
    monkeypatch.setattr(eng_mod, "get_engine", lambda: engine)

    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add(User(id=1, username="test"))
        s.add(UserProfile(user_id=1, preferences={}, memory_enabled=True))
        s.add(Teacher(id=1, name="李老师", gender="male"))
        s.add(TeacherSchedule(id=1, teacher_id=1, date="2026-06-01",
                              time_slot="14:00-15:00", status="available"))
        s.commit()
    return engine


def test_create_appointment_marks_slot_booked(mem_engine):
    from src.db.repositories.appointment_repo import AppointmentRepository
    repo = AppointmentRepository(engine=mem_engine)
    appt_id = repo.create(user_id=1, teacher_id=1, schedule_id=1, topic="选校咨询")
    assert appt_id > 0

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    with sessionmaker(bind=mem_engine)() as s:
        row = s.execute(text("SELECT status FROM teacher_schedule WHERE id=1")).fetchone()
    assert row[0] == "booked"


def test_create_fails_on_unavailable_slot(mem_engine):
    from src.db.repositories.appointment_repo import AppointmentRepository
    repo = AppointmentRepository(engine=mem_engine)
    repo.create(user_id=1, teacher_id=1, schedule_id=1)
    with pytest.raises(ValueError):
        repo.create(user_id=1, teacher_id=1, schedule_id=1)
