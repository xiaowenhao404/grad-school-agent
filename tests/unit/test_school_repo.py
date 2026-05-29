"""单测：SchoolProgramRepository.filter_programs — 内存 SQLite。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, School, SchoolProgram


@pytest.fixture
def mem_engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # 注入内存 engine
    import src.db.engine as eng_mod
    eng_mod.get_engine.cache_clear()
    monkeypatch.setattr(eng_mod, "get_engine", lambda: engine)

    Session = sessionmaker(bind=engine)
    with Session() as s:
        s.add(School(names=["MIT"], country="美国", country_en="USA", qs_rank=1,
                     official_site="https://mit.edu", intro="顶尖理工"))
        s.add(School(names=["Stanford"], country="美国", country_en="USA", qs_rank=3,
                     official_site="https://stanford.edu", intro="斯坦福"))
        s.add(School(names=["Oxford"], country="英国", country_en="UK", qs_rank=4,
                     official_site="https://ox.ac.uk", intro="牛津"))
        s.commit()
        # programs: school_id 1=MIT, 2=Stanford, 3=Oxford
        s.add(SchoolProgram(school_id=1, program_names=["MSCS"], major_category="CS",
                            duration_months=12, tuition_per_year=60000, currency="USD",
                            ielts_min=7.0, toefl_min=100))
        s.add(SchoolProgram(school_id=2, program_names=["MSEE"], major_category="EE",
                            duration_months=18, tuition_per_year=55000, currency="USD",
                            ielts_min=6.5, toefl_min=90))
        s.add(SchoolProgram(school_id=3, program_names=["MSc CS"], major_category="CS",
                            duration_months=12, tuition_per_year=30000, currency="GBP",
                            ielts_min=7.0, toefl_min=100))
        s.add(SchoolProgram(school_id=1, program_names=["MEng EECS"], major_category="EE",
                            duration_months=12, tuition_per_year=65000, currency="USD"))
        s.commit()
    return engine


def test_filter_by_country(mem_engine):
    from src.db.repositories.school_repo import SchoolProgramRepository
    repo = SchoolProgramRepository(engine=mem_engine)
    ids = repo.filter_programs({"country": "美国"})
    assert len(ids) == 3


def test_filter_by_major_and_tuition(mem_engine):
    from src.db.repositories.school_repo import SchoolProgramRepository
    repo = SchoolProgramRepository(engine=mem_engine)
    ids = repo.filter_programs({"major_category": "CS", "tuition_range": [0, 50000]})
    assert len(ids) == 1


def test_filter_empty_prefs_returns_all(mem_engine):
    from src.db.repositories.school_repo import SchoolProgramRepository
    repo = SchoolProgramRepository(engine=mem_engine)
    ids = repo.filter_programs({})
    assert len(ids) == 4


def test_filter_qs_range(mem_engine):
    from src.db.repositories.school_repo import SchoolProgramRepository
    repo = SchoolProgramRepository(engine=mem_engine)
    ids = repo.filter_programs({"qs_rank_range": [1, 2]})
    assert len(ids) == 2
