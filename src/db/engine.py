"""共享 SQLAlchemy engine 工厂。"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@lru_cache(maxsize=1)
def get_engine():
    from src.utils.config_loader import load_settings
    cfg = load_settings()
    path = cfg["db"]["path"]
    echo = cfg["db"].get("echo_sql", False)
    return create_engine(f"sqlite:///{path}", echo=echo, connect_args={"check_same_thread": False})


def make_session(engine=None) -> Session:
    eng = engine or get_engine()
    return sessionmaker(bind=eng)()
