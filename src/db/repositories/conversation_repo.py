"""Conversation & Message 访问。"""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from src.db.engine import get_engine


def _session():
    return sessionmaker(bind=get_engine())()


class ConversationRepository:
    def start(self, user_id: int) -> int:
        from src.db.models import Conversation
        with _session() as s:
            conv = Conversation(user_id=user_id)
            s.add(conv)
            s.commit()
            s.refresh(conv)
            return conv.id

    def list_recent(self, user_id: int, limit: int = 20) -> list[dict]:
        from sqlalchemy import text
        sql = text("SELECT * FROM conversations WHERE user_id=:uid ORDER BY started_at DESC LIMIT :limit")
        with _session() as s:
            rows = s.execute(sql, {"uid": user_id, "limit": limit}).mappings().fetchall()
        return [dict(r) for r in rows]

    def add_message(self, conversation_id: int, role: str, content: str,
                    agent_name: str | None = None) -> int:
        from src.db.models import Message
        with _session() as s:
            msg = Message(conversation_id=conversation_id, role=role,
                          content=content, agent_name=agent_name)
            s.add(msg)
            s.commit()
            s.refresh(msg)
            return msg.id

    def list_messages(self, conversation_id: int) -> list[dict]:
        from sqlalchemy import text
        sql = text("SELECT * FROM messages WHERE conversation_id=:cid ORDER BY created_at")
        with _session() as s:
            rows = s.execute(sql, {"cid": conversation_id}).mappings().fetchall()
        return [dict(r) for r in rows]

    def clear(self, user_id: int) -> None:
        from sqlalchemy import text
        with _session() as s:
            conv_ids = [r[0] for r in s.execute(
                text("SELECT id FROM conversations WHERE user_id=:uid"), {"uid": user_id}
            ).fetchall()]
            if conv_ids:
                placeholders = ",".join(str(i) for i in conv_ids)
                s.execute(text(f"DELETE FROM messages WHERE conversation_id IN ({placeholders})"))
            s.execute(text("DELETE FROM conversations WHERE user_id=:uid"), {"uid": user_id})
            s.commit()
