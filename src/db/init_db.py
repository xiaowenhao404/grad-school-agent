"""初始化数据库 + 导入 seed 数据。

用法：`uv run python -m src.db.init_db`
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import (
    Base,
    School,
    SchoolProgram,
    Teacher,
    TeacherSchedule,
    User,
    UserProfile,
    Conversation,
    Message,
    Appointment,
)


def create_all_tables(db_url: str = "sqlite:///data/grad_school.db") -> None:
    """根据 ORM models 创建所有表。"""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    print("[init_db] 所有表创建完成")


def import_seed_data(seed_dir: Path, db_url: str = "sqlite:///data/grad_school.db") -> dict:
    """从 data/seed/ 导入 teachers / schools / programs（JSON 格式）。

    Returns:
        统计 dict：{teachers: int, schools: int, programs: int, schedules: int}
    """
    db_url = db_url
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    stats = {"teachers": 0, "schools": 0, "programs": 0, "schedules": 0}

    try:
        # 1. 导入 schools
        schools_file = seed_dir / "schools.json"
        if schools_file.exists():
            with open(schools_file, "r", encoding="utf-8") as f:
                schools_data = json.load(f)
            for item in schools_data:
                school = School(
                    names=item.get("names", []),
                    country=item.get("country", ""),
                    country_en=item.get("country_en"),
                    city=item.get("city"),
                    address=item.get("address"),
                    qs_rank=item.get("qs_rank"),
                    official_site=item.get("official_site"),
                    intro=item.get("intro"),
                )
                session.add(school)
            stats["schools"] = len(schools_data)
            print(f"[init_db] 导入 {stats['schools']} 所学校")

        # 2. 导入 teachers
        teachers_file = seed_dir / "teachers.json"
        if teachers_file.exists():
            with open(teachers_file, "r", encoding="utf-8") as f:
                teachers_data = json.load(f)
            for item in teachers_data:
                teacher = Teacher(
                    name=item.get("name", ""),
                    gender=item.get("gender", "other"),
                    bio=item.get("bio"),
                    study_abroad=item.get("study_abroad"),
                    work_experience=item.get("work_experience"),
                    expertise_regions=item.get("expertise_regions"),
                    expertise_majors=item.get("expertise_majors"),
                    avatar_url=item.get("avatar_url"),
                    rating=item.get("rating"),
                )
                session.add(teacher)
            stats["teachers"] = len(teachers_data)
            print(f"[init_db] 导入 {stats['teachers']} 位老师")

        # 3. 导入 programs（需要 schools 已导入）
        programs_file = seed_dir / "programs.json"
        if programs_file.exists() and schools_file.exists():
            with open(programs_file, "r", encoding="utf-8") as f:
                programs_data = json.load(f)
            for item in programs_data:
                program = SchoolProgram(
                    school_id=item.get("school_id"),
                    program_names=item.get("program_names", []),
                    program_short_names=item.get("program_short_names"),
                    tags=item.get("tags"),
                    major_category=item.get("major_category", "其他"),
                    duration_months=item.get("duration_months", 12),
                    tuition_per_year=item.get("tuition_per_year", 0),
                    currency=item.get("currency", "USD"),
                    ielts_min=item.get("ielts_min"),
                    toefl_min=item.get("toefl_min"),
                    program_url=item.get("program_url"),
                    description_short=item.get("description_short"),
                )
                session.add(program)
            stats["programs"] = len(programs_data)
            print(f"[init_db] 导入 {stats['programs']} 个项目")

        session.commit()
        print("[init_db] Seed 数据导入成功")

        # 4. 导入 teacher_schedule
        schedule_file = seed_dir / "teacher_schedule.json"
        if schedule_file.exists():
            with open(schedule_file, "r", encoding="utf-8") as f:
                schedule_data = json.load(f)
            from .models import TeacherSchedule
            for item in schedule_data:
                session.add(TeacherSchedule(
                    teacher_id=item["teacher_id"],
                    date=item["date"],
                    time_slot=item["time_slot"],
                    status=item.get("status", "available"),
                ))
            session.commit()
            stats["schedules"] = len(schedule_data)
            print(f"[init_db] 导入 {stats['schedules']} 条时间槽")

    except Exception as e:
        session.rollback()
        print(f"[init_db] 导入失败: {e}")
        raise
    finally:
        session.close()

    return stats


def create_default_user(db_url: str = "sqlite:///data/grad_school.db") -> None:
    """创建默认用户（id=1），用于课程项目阶段。"""
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 检查是否已存在
        existing = session.query(User).filter_by(id=1).first()
        if not existing:
            user = User(id=1, username="default_user")
            profile = UserProfile(user_id=1, preferences={}, memory_enabled=True)
            session.add(user)
            session.add(profile)
            session.commit()
            print("[init_db] 默认用户创建成功")
        else:
            print("[init_db] 默认用户已存在")
    except Exception as e:
        session.rollback()
        print(f"[init_db] 创建默认用户失败: {e}")
    finally:
        session.close()


def main():
    """主函数：建表 + 导入 seed 数据。"""
    import os

    # 确保 data 目录存在
    os.makedirs("data", exist_ok=True)

    db_url = "sqlite:///data/grad_school.db"
    seed_dir = Path("data/seed")

    print("[init_db] 开始初始化数据库...")
    create_all_tables(db_url)

    if seed_dir.exists():
        stats = import_seed_data(seed_dir)
        print(f"[init_db] 导入统计: {stats}")

    create_default_user(db_url)
    print("[init_db] 数据库初始化完成！")


if __name__ == "__main__":
    main()
