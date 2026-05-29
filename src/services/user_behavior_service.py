"""UserBehaviorService — 用户行为分析页面服务。

UI 的"用户行为分析"页面通过本服务展示画像。
"""
from __future__ import annotations


class UserBehaviorService:
    def get_profile(self, user_id: int) -> dict:
        """返回 {preferences, memory_enabled, updated_at}。"""
        raise NotImplementedError

    def render_profile_summary(self, user_id: int) -> str:
        """调用 UserBehaviorAgent.display 生成中文画像描述。"""
        raise NotImplementedError

    def toggle_memory(self, user_id: int, enabled: bool) -> None:
        """UI 开关：是否启用偏好记忆。"""
        raise NotImplementedError

    def list_recent_conversations(self, user_id: int, limit: int = 10) -> list[dict]:
        """画像页面可附带列出最近会话样本，方便用户理解画像由何而来。"""
        raise NotImplementedError
