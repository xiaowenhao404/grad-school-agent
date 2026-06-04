"""User & UserProfile 访问。"""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from src.db.engine import get_engine


def _session():
    return sessionmaker(bind=get_engine())()


class UserRepository:
    def get_or_create(self, username: str) -> dict:
        from src.db.models import User, UserProfile
        with _session() as s:
            user = s.query(User).filter_by(username=username).first()
            if not user:
                user = User(username=username)
                s.add(user)
                s.flush()
                s.add(UserProfile(user_id=user.id, preferences={}, memory_enabled=True))
                s.commit()
                s.refresh(user)
            return {"id": user.id, "username": user.username}

    def get_profile(self, user_id: int) -> dict:
        from src.db.models import UserProfile
        with _session() as s:
            p = s.get(UserProfile, user_id)
            if p is None:
                return {"preferences": {}, "memory_enabled": True}
            return {"preferences": p.preferences or {}, "memory_enabled": p.memory_enabled}

    def update_profile(self, user_id: int, new_preferences: dict) -> None:
        from src.db.models import UserProfile
        with _session() as s:
            p = s.get(UserProfile, user_id)
            if p is None:
                s.add(UserProfile(user_id=user_id, preferences=new_preferences, memory_enabled=True))
            else:
                merged = _merge_prefs(p.preferences or {}, new_preferences)
                p.preferences = merged
            s.commit()

    def set_memory_enabled(self, user_id: int, enabled: bool) -> None:
        from src.db.models import UserProfile
        with _session() as s:
            p = s.get(UserProfile, user_id)
            if p:
                p.memory_enabled = enabled
                s.commit()

    def clear_profile(self, user_id: int) -> None:
        from src.db.models import UserProfile
        with _session() as s:
            p = s.get(UserProfile, user_id)
            if p:
                p.preferences = {}
                s.commit()


def _merge_prefs(old: dict, new: dict) -> dict:
    """合并偏好：最新一轮覆盖旧值（用户口头改了就该改），null/空值跳过。

    对于嵌套 dict（如 school_prefs / teacher_prefs），做一层深度合并：
    内层标量/列表也走"新值覆盖旧值"逻辑，未提及的字段保留。
    """
    result = dict(old)
    for k, v in new.items():
        if v is None or v == "" or v == [] or v == {}:
            continue
        old_v = result.get(k)
        if isinstance(v, dict) and isinstance(old_v, dict):
            # 嵌套字典：内层字段也是新值覆盖
            merged = dict(old_v)
            for ik, iv in v.items():
                if iv is None or iv == "" or iv == [] or iv == {}:
                    continue
                merged[ik] = iv
            result[k] = merged
        else:
            result[k] = v
    return result
