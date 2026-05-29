"""单测：TeacherRepository.search_by_preferences。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, Teacher


@pytest.fixture
def mem_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    import src.db.engine as eng_mod
    eng_mod.get_engine.cache_clear()
    monkeypatch.setattr(eng_mod, "get_engine", lambda: engine)

    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add(Teacher(name="李老师", gender="male", expertise_regions="美国,加拿大",
                      expertise_majors="CS,EE", bio="专注北美申请"))
        s.add(Teacher(name="王老师", gender="female", expertise_regions="英国,澳洲",
                      expertise_majors="Business", bio="英澳专家"))
        s.add(Teacher(name="张老师", gender="male", expertise_regions="美国",
                      expertise_majors="DS,CS", bio="数据科学"))
        s.commit()
    return engine


def test_filter_by_gender(mem_engine):
    from src.db.repositories.teacher_repo import TeacherRepository
    repo = TeacherRepository(engine=mem_engine)
    results = repo.search_by_preferences({"gender": "female"})
    assert len(results) == 1
    assert results[0]["name"] == "王老师"


def test_filter_by_region(mem_engine):
    from src.db.repositories.teacher_repo import TeacherRepository
    repo = TeacherRepository(engine=mem_engine)
    results = repo.search_by_preferences({"expertise_regions": "美国"})
    assert len(results) == 2


def test_filter_any_gender_returns_all(mem_engine):
    from src.db.repositories.teacher_repo import TeacherRepository
    repo = TeacherRepository(engine=mem_engine)
    results = repo.search_by_preferences({"gender": "any"})
    assert len(results) == 3
