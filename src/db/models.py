"""SQLAlchemy ORM 模型定义。

约定：所有表和字段必须写 `comment=`，与 `docs/DB_SCHEMA.md` 实时同步。
详见 DEV_SPEC.md 附录 A。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 风格的 Declarative Base。"""


# ============================================================
# 用户与画像
# ============================================================
class User(Base):
    """用户表 — 系统使用者基础信息。课程项目阶段为单用户简单模型。"""
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    id = Column(Integer, primary_key=True, comment="用户 ID")
    username = Column(String(64), unique=True, nullable=False, comment="用户名（唯一）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user")
    appointments = relationship("Appointment", back_populates="user")


class UserProfile(Base):
    """用户画像表 — 由 post-hook 异步抽取并合并的偏好信息。"""
    __tablename__ = "user_profile"
    __table_args__ = {"comment": "用户画像（偏好记忆）"}

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, comment="用户 ID")
    preferences = Column(
        JSON,
        default=dict,
        comment="偏好 JSON：{interested_countries, interested_majors, tuition_range_usd, qs_rank_range, gender_preference_for_teacher, keywords}",
    )
    memory_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用偏好记忆。False 时 pre/post hook 全部跳过",
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="最后更新时间",
    )

    user = relationship("User", back_populates="profile")


# ============================================================
# 会话与消息
# ============================================================
class Conversation(Base):
    """会话表 — 一次完整对话窗口。点击"清空对话"会开新一行。"""
    __tablename__ = "conversations"
    __table_args__ = {"comment": "对话会话"}

    id = Column(Integer, primary_key=True, comment="会话 ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所属用户")
    started_at = Column(DateTime, default=datetime.utcnow, comment="开始时间")

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """单条消息 — 记录哪个 Agent 生成，便于追溯与 demo 讲解。"""
    __tablename__ = "messages"
    __table_args__ = {"comment": "单条对话消息"}

    id = Column(Integer, primary_key=True, comment="消息 ID")
    conversation_id = Column(
        Integer, ForeignKey("conversations.id"), nullable=False, comment="所属会话"
    )
    role = Column(String(16), nullable=False, comment="消息角色：user / assistant / system")
    agent_name = Column(
        String(32),
        nullable=True,
        comment="由哪个 Agent 生成：task_classifier / consultant / school_selection / appointment / user_behavior（user 消息为空）",
    )
    content = Column(Text, nullable=False, comment="消息正文")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    conversation = relationship("Conversation", back_populates="messages")


# ============================================================
# 老师与时间槽
# ============================================================
class Teacher(Base):
    """咨询老师表。"""
    __tablename__ = "teachers"
    __table_args__ = {"comment": "咨询老师"}

    id = Column(Integer, primary_key=True, comment="老师 ID")
    name = Column(String(64), nullable=False, comment="姓名")
    gender = Column(String(8), nullable=False, comment="性别：male / female / other")
    bio = Column(Text, nullable=True, comment="简介（自由文本，会进入 Chroma teachers collection）")
    study_abroad = Column(
        String(255),
        nullable=True,
        comment="留学经历摘要（如 'MIT MS in CS, 2018-2020'）",
    )
    work_experience = Column(Text, nullable=True, comment="工作经历摘要")
    expertise_regions = Column(
        String(255),
        nullable=True,
        comment="擅长地区，逗号分隔（如 '美国,英国,加拿大'）",
    )
    expertise_majors = Column(
        String(255),
        nullable=True,
        comment="擅长专业，逗号分隔（如 'CS,EE,DS'）",
    )
    avatar_url = Column(String(255), nullable=True, comment="头像 URL")
    rating = Column(Float, nullable=True, comment="评分（如 4.8）")

    schedule = relationship("TeacherSchedule", back_populates="teacher")
    appointments = relationship("Appointment", back_populates="teacher")


class TeacherSchedule(Base):
    """老师可预约时间槽。由管理员/老师批量录入。"""
    __tablename__ = "teacher_schedule"
    __table_args__ = {"comment": "老师可预约时间槽"}

    id = Column(Integer, primary_key=True, comment="时间槽 ID")
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, comment="老师 ID")
    date = Column(String(10), nullable=False, comment="日期 YYYY-MM-DD")
    time_slot = Column(String(16), nullable=False, comment="时间段（如 14:00-15:00）")
    status = Column(
        String(16),
        nullable=False,
        default="available",
        comment="状态：available / booked / blocked",
    )

    teacher = relationship("Teacher", back_populates="schedule")


# ============================================================
# 预约订单
# ============================================================
class Appointment(Base):
    """预约订单。AppointmentAgent 在确认后写入。"""
    __tablename__ = "appointments"
    __table_args__ = {"comment": "预约订单"}

    id = Column(Integer, primary_key=True, comment="预约 ID（即订单号）")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="预约用户")
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, comment="预约老师")
    schedule_id = Column(
        Integer, ForeignKey("teacher_schedule.id"), nullable=False, comment="预约的时间槽"
    )
    topic = Column(Text, nullable=True, comment="预约话题（用户填写）")
    status = Column(
        String(16),
        nullable=False,
        default="confirmed",
        comment="状态：pending / confirmed / cancelled",
    )
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    user = relationship("User", back_populates="appointments")
    teacher = relationship("Teacher", back_populates="appointments")


# ============================================================
# 学校与项目
# ============================================================
class School(Base):
    """学校表（父级）。"""
    __tablename__ = "schools"
    __table_args__ = {"comment": "学校（父级）"}

    id = Column(Integer, primary_key=True, comment="学校 ID")
    names = Column(
        JSON,
        nullable=False,
        comment="名称变体数组，含中英文全称、简称等，如 ['MIT', 'Massachusetts Institute of Technology', '麻省理工学院']",
    )
    country = Column(String(32), nullable=False, comment="所在国家（中文）")
    country_en = Column(String(32), nullable=True, comment="所在国家（英文）")
    city = Column(String(64), nullable=True, comment="所在城市")
    address = Column(String(255), nullable=True, comment="详细地址")
    qs_rank = Column(Integer, nullable=True, comment="QS 综合排名")
    official_site = Column(String(255), nullable=True, comment="官网 URL")
    intro = Column(Text, nullable=True, comment="学校总介绍")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    programs = relationship("SchoolProgram", back_populates="school")


class SchoolProgram(Base):
    """学校项目表（子级）。一所学校下有多个项目，每个项目学制/学费各异。"""
    __tablename__ = "school_programs"
    __table_args__ = {"comment": "学校下的具体申请项目"}

    id = Column(Integer, primary_key=True, comment="项目 ID")
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, comment="所属学校")
    program_names = Column(
        JSON,
        nullable=False,
        comment="项目中英文全称，如 ['Master of Science in Computer Science', '计算机科学硕士']",
    )
    program_short_names = Column(
        JSON,
        nullable=True,
        comment="项目多简称变体，如 ['MSCS', 'CS Master', 'MCS']",
    )
    tags = Column(
        JSON,
        nullable=True,
        comment="分类标签，如 ['CS', 'AI', '泛计算机']",
    )
    major_category = Column(
        String(32),
        nullable=False,
        comment="专业大类：CS / EE / DS / Business / 其他",
    )
    duration_months = Column(Integer, nullable=False, comment="学制（月）")
    tuition_per_year = Column(Float, nullable=False, comment="学费/年（数值）")
    currency = Column(String(8), nullable=False, default="USD", comment="币种（USD / GBP / CNY 等）")
    ielts_min = Column(Float, nullable=True, comment="雅思最低要求（如 7.0）")
    toefl_min = Column(Float, nullable=True, comment="托福最低要求（如 100）")
    program_url = Column(String(255), nullable=True, comment="学院官网项目链接")
    description_short = Column(Text, nullable=True, comment="项目简介（详细描述进入 Chroma schools collection）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    school = relationship("School", back_populates="programs")
