"""单测：init_db seed 导入计数。"""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.db.models import Base


@pytest.fixture
def seed_dir(tmp_path):
    """创建最小 seed 数据集。"""
    schools = [{"names": ["MIT"], "country": "美国", "country_en": "USA", "qs_rank": 1,
                "official_site": "https://mit.edu", "intro": "顶尖理工"}]
    teachers = [{"name": "李老师", "gender": "male", "bio": "专注北美"}]
    programs = [{"school_id": 1, "program_names": ["MSCS"], "major_category": "CS",
                 "duration_months": 12, "tuition_per_year": 60000, "currency": "USD"}]
    schedules = [{"teacher_id": 1, "date": "2026-06-01", "time_slot": "14:00-15:00", "status": "available"},
                 {"teacher_id": 1, "date": "2026-06-01", "time_slot": "15:00-16:00", "status": "available"}]

    (tmp_path / "schools.json").write_text(json.dumps(schools), encoding="utf-8")
    (tmp_path / "teachers.json").write_text(json.dumps(teachers), encoding="utf-8")
    (tmp_path / "programs.json").write_text(json.dumps(programs), encoding="utf-8")
    (tmp_path / "teacher_schedule.json").write_text(json.dumps(schedules), encoding="utf-8")
    return tmp_path


def test_import_seed_data_counts(seed_dir, tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    from src.db.init_db import create_all_tables, import_seed_data
    create_all_tables(db_url)
    stats = import_seed_data(seed_dir, db_url=db_url)

    assert stats["schools"] == 1
    assert stats["teachers"] == 1
    assert stats["programs"] == 1
    assert stats["schedules"] == 2
