"""
子任务表模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON, Index

from app.database import Base


class SubTask(Base):
    __tablename__ = "sub_task"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("task.id"), nullable=False, index=True, comment="所属任务")
    module_id = Column(String(36), ForeignKey("module.id"), nullable=True, index=True, comment="所属模块（可为空）")
    name = Column(String(200), nullable=False, comment="子任务名称")
    description = Column(Text, default="", comment="具体内容")
    deliverable = Column(Text, default="", comment="交付物描述")
    acceptance = Column(Text, default="", comment="验收标准")
    type = Column(String(20), default="once", comment="类型: once/recurring")
    status = Column(String(20), default="pending", index=True, comment="状态: pending/assigned/in_progress/review/rework/blocked/done/cancelled")
    priority = Column(String(10), default="medium", comment="优先级: high/medium/low")
    assigned_agent = Column(String(36), ForeignKey("agent.id"), nullable=True, index=True, comment="指派的 Agent")
    current_session_id = Column(String(200), nullable=True, comment="当前处理的 OpenClaw 会话 ID")
    rework_count = Column(Integer, default=0, comment="返工次数")
    recurring_config = Column(JSON, nullable=True, comment="循环任务配置")
    remarks = Column(Text, nullable=True, comment="备注，如取消原因")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 复合索引：按 Agent 查其某状态的子任务
    __table_args__ = (
        Index("ix_sub_task_agent_status", "assigned_agent", "status"),
    )
