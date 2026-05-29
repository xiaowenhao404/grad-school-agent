"""TeacherService — 老师管理面板服务。

UI 的"老师管理"与"老师时间表"页面共用本服务。
"""
from __future__ import annotations


class TeacherService:
    def list_teachers(self) -> list[dict]:
        raise NotImplementedError

    def get_teacher_detail(self, teacher_id: int) -> dict | None:
        raise NotImplementedError

    def upsert_teacher(self, payload: dict) -> int:
        """新增/修改老师信息。修改后需要同步刷新 teachers Chroma collection。"""
        raise NotImplementedError

    def list_schedule(self, teacher_id: int) -> list[dict]:
        """该老师全部时间槽（含 booked/blocked）。"""
        raise NotImplementedError

    def add_schedule_slots(self, teacher_id: int, slots: list[dict]) -> int:
        """批量添加可预约时间槽。"""
        raise NotImplementedError
