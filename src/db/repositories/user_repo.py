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
    """合并偏好：list 字段去重合并，标量字段覆盖，null 跳过。"""
    result = dict(old)
    for k, v in new.items():
        if v is None:
            continue
        if isinstance(v, list) and isinstance(result.get(k), list):
            result[k] = list(dict.fromkeys(result[k] + v))
        elif isinstance(v, list) and len(v) == 2 and isinstance(v[0], (int, float)):
            # 区间取并集
            old_v = result.get(k)
            if isinstance(old_v, list) and len(old_v) == 2:
                result[k] = [min(old_v[0], v[0]), max(old_v[1], v[1])]
            else:
                result[k] = v
        else:
            result[k] = v
    return result
