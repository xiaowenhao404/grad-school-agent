"""Repositories — 数据访问层，业务代码只依赖本层不直连 ORM。"""

from .appointment_repo import AppointmentRepository
from .conversation_repo import ConversationRepository
from .school_repo import SchoolRepository, SchoolProgramRepository
from .teacher_repo import TeacherRepository, TeacherScheduleRepository
from .user_repo import UserRepository

__all__ = [
    "AppointmentRepository",
    "ConversationRepository",
    "SchoolRepository",
    "SchoolProgramRepository",
    "TeacherRepository",
    "TeacherScheduleRepository",
    "UserRepository",
]
