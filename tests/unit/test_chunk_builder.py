"""单测：SQLite → school chunk 数量与 metadata 字段。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, School, SchoolProgram


@pytest.fixture
def mem_engine_with_data(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    import src.db.engine as eng_mod
    eng_mod.get_engine.cache_clear()
    monkeypatch.setattr(eng_mod, "get_engine", lambda: engine)

    with sessionmaker(bind=engine)() as s:
        s.add(School(id=1, names=["MIT"], country="美国", country_en="USA", qs_rank=1,
                     official_site="https://mit.edu", intro="顶尖理工"))
        s.add(SchoolProgram(id=1, school_id=1, program_names=["MSCS"], major_category="CS",
                            duration_months=12, tuition_per_year=60000, currency="USD"))
        s.add(SchoolProgram(id=2, school_id=1, program_names=["MEng"], major_category="EE",
                            duration_months=12, tuition_per_year=65000, currency="USD"))
        s.commit()
    return engine


def test_school_chunks_count(mem_engine_with_data):
    from src.rag.ingestion.pipeline import _build_school_chunks_from_sqlite
    chunks = _build_school_chunks_from_sqlite()
    # 1 school_overview + 2 programs = 3 chunks
    assert len(chunks) == 3


def test_program_chunk_has_program_id(mem_engine_with_data):
    from src.rag.ingestion.pipeline import _build_school_chunks_from_sqlite
    chunks = _build_school_chunks_from_sqlite()
    prog_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "program"]
    assert len(prog_chunks) == 2
    assert all("program_id" in c.metadata for c in prog_chunks)
    assert {c.metadata["program_id"] for c in prog_chunks} == {1, 2}


def test_school_overview_chunk_has_school_id(mem_engine_with_data):
    from src.rag.ingestion.pipeline import _build_school_chunks_from_sqlite
    chunks = _build_school_chunks_from_sqlite()
    overview = [c for c in chunks if c.metadata.get("chunk_type") == "school_overview"]
    assert len(overview) == 1
    assert overview[0].metadata["school_id"] == 1
