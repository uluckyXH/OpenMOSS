"""配置态 Agent 定时任务 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base import ManagedAgentScheduleType


class ManagedAgentScheduleCreateRequest(BaseModel):
    """创建定时任务。"""

    name: str = Field(..., min_length=1, max_length=200)
    enabled: bool = True
    schedule_type: ManagedAgentScheduleType = Field(..., description="interval/cron")
    schedule_expr: str = Field(..., min_length=1, description="间隔值或 5 段 cron 表达式")
    timeout_seconds: int = Field(..., ge=60)
    model_override: Optional[str] = None
    execution_options_json: Optional[str] = None
    schedule_message_content: str = Field(..., min_length=1, description="定时唤醒提示词")


class ManagedAgentScheduleUpdateRequest(BaseModel):
    """更新定时任务。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    enabled: Optional[bool] = None
    schedule_type: Optional[ManagedAgentScheduleType] = Field(default=None, description="interval/cron")
    schedule_expr: Optional[str] = Field(default=None, min_length=1, description="间隔值或 5 段 cron 表达式")
    timeout_seconds: Optional[int] = Field(default=None, ge=60)
    model_override: Optional[str] = None
    execution_options_json: Optional[str] = None
    schedule_message_content: Optional[str] = Field(default=None, min_length=1, description="定时唤醒提示词")

    @model_validator(mode="after")
    def validate_nullable_fields(self):
        non_nullable_fields = {
            "name",
            "enabled",
            "schedule_type",
            "schedule_expr",
            "timeout_seconds",
            "schedule_message_content",
        }
        for field_name in non_nullable_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class ManagedAgentScheduleResponse(BaseModel):
    """定时任务响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    name: str
    enabled: bool
    schedule_type: ManagedAgentScheduleType
    schedule_expr: str
    timeout_seconds: int
    model_override: Optional[str] = None
    execution_options_json: Optional[str] = None
    schedule_message_content: str
    created_at: datetime
    updated_at: datetime

