"""
任务表模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey

from app.database import Base


class Task(Base):
    __tablename__ = "task"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, comment="任务名称")
    description = Column(Text, default="", comment="任务描述")
    type = Column(String(20), default="once", comment="任务类型: once/recurring")
    status = Column(String(20), default="planning", index=True, comment="状态: planning/active/in_progress/completed/archived")
    team_id = Column(String(36), ForeignKey("team.id"), nullable=True, index=True, comment="所属团队ID")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
