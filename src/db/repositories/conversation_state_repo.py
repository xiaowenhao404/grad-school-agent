"""ConversationState 访问 — 持久化跨轮 graph state 字段（appointment_slots / metadata）。

Why: AppointmentAgent 是多轮状态机，必须在 turn 之间保留 current_stage、
candidate_teachers、selected_teacher 等字段，否则用户输入序号"2"时
classifier 会重新路由回 collect_preferences。
"""
from __future__ import annotations

import json
from sqlalchemy.orm import sessionmaker

from src.db.engine import get_engine


class ConversationStateRepository:
    def __init__(self, engine=None):
        self._engine = engine or get_engine()

    def _s(self):
        return sessionmaker(bind=self._engine)()

    def load(self, conversation_id: int) -> dict:
        """读出 {appointment_slots, metadata} dict；不存在时返回空 dict。"""
        from src.db.models import ConversationState
        with self._s() as s:
            row = s.get(ConversationState, conversation_id)
            if row is None:
                return {}
            out: dict = {}
            if row.appointment_slots:
                try:
                    out["appointment_slots"] = json.loads(row.appointment_slots)
                except Exception:
                    pass
            if row.metadata_json:
                try:
                    out["metadata"] = json.loads(row.metadata_json)
                except Exception:
                    pass
            return out

    def save(self, conversation_id: int, *,
             appointment_slots: dict | None = None,
             metadata: dict | None = None) -> None:
        """UPSERT；None 字段不变更，传 {} 则清空。"""
        from src.db.models import ConversationState
        with self._s() as s:
            row = s.get(ConversationState, conversation_id)
            if row is None:
                row = ConversationState(conversation_id=conversation_id)
                s.add(row)
            if appointment_slots is not None:
                row.appointment_slots = json.dumps(appointment_slots, ensure_ascii=False)
            if metadata is not None:
                row.metadata_json = json.dumps(metadata, ensure_ascii=False)
            s.commit()

    def clear(self, conversation_id: int) -> None:
        """整体清空（如 clear_conversation 时调用）。"""
        from src.db.models import ConversationState
        with self._s() as s:
            row = s.get(ConversationState, conversation_id)
            if row is not None:
                s.delete(row)
                s.commit()
