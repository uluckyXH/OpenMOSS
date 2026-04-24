"""
配置态 Agent 数据模型

本模块定义「智能体配置中心」的核心数据表，与现有运行态 agent 表共存。
设计文档：dev-docs/agent-config-center/03-数据库设计.md
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ManagedAgent(Base):
    """配置态 Agent 主表，只保存跨平台通用字段"""
    __tablename__ = "managed_agent"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, comment="管理端显示名称")
    slug = Column(String(100), unique=True, nullable=False, comment="稳定标识，用于 URL 和内部引用")
    role = Column(String(20), nullable=False, index=True, comment="角色: planner/executor/reviewer/patrol")
    description = Column(Text, default="", comment="描述")

    host_platform = Column(
        String(30), nullable=False, default="openclaw",
        comment="宿主平台: openclaw / codex_cli / claude_code / generic_api_agent"
    )
    deployment_mode = Column(
        String(30), nullable=False,
        comment="部署模式: create_sub_agent / bind_existing_agent / bind_main_agent"
    )
    host_access_mode = Column(
        String(20), nullable=False, default="local",
        comment="宿主访问方式: local / remote"
    )

    status = Column(
        String(20), default="draft", index=True,
        comment="draft / configured / deployed / disabled / archived"
    )
    runtime_agent_id = Column(String(36), nullable=True, index=True, comment="关联运行态 agent.id")
    config_version = Column(Integer, default=1, comment="当前目标部署版本号")
    deployed_config_version = Column(Integer, nullable=True, comment="当前已部署到运行态的版本号")

    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class ManagedAgentHostConfig(Base):
    """宿主平台配置（1:1）"""
    __tablename__ = "managed_agent_host_config"

    id = Column(String(36), primary_key=True, default=_uuid)
    managed_agent_id = Column(String(36), nullable=False, unique=True, index=True, comment="关联 managed_agent.id")
    host_platform = Column(String(30), nullable=False, comment="宿主平台")
    host_agent_identifier = Column(String(100), nullable=True, comment="宿主平台中的 Agent 标识")
    workdir_path = Column(String(500), nullable=True, comment="宿主平台中的工作目录")
    host_config_payload_encrypted = Column(Text, nullable=True, comment="宿主平台特有配置（预留加密）")
    host_metadata_json = Column(Text, nullable=True, comment="宿主平台非敏感扩展信息 JSON")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class ManagedAgentPromptAsset(Base):
    """Prompt 资产（1:1）"""
    __tablename__ = "managed_agent_prompt_asset"

    id = Column(String(36), primary_key=True, default=_uuid)
    managed_agent_id = Column(String(36), nullable=False, unique=True, index=True, comment="关联 managed_agent.id")
    template_role = Column(String(50), nullable=True, comment="初始化使用的模板角色")
    system_prompt_content = Column(Text, default="", comment="系统提示词")
    persona_prompt_content = Column(Text, default="", comment="人格提示词")
    identity_content = Column(Text, default="", comment="身份内容")
    host_render_strategy = Column(
        String(50), default="host_default",
        comment="宿主平台渲染策略: host_default / openclaw_workspace_files / openclaw_inline_schedule"
    )
    authority_source = Column(String(30), default="database", comment="当前阶段固定 database，预留扩展")
    notes = Column(Text, nullable=True, comment="内部备注")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class ManagedAgentSchedule(Base):
    """配置态 Agent 定时任务（1:N）"""
    __tablename__ = "managed_agent_schedule"

    id = Column(String(36), primary_key=True, default=_uuid)
    managed_agent_id = Column(String(36), nullable=False, index=True, comment="关联 managed_agent.id")
    name = Column(String(200), nullable=False, comment="任务名称")
    enabled = Column(Boolean, default=True, comment="是否启用")
    schedule_type = Column(String(20), default="interval", comment="interval / cron")
    schedule_expr = Column(String(100), default="15m", comment="执行间隔或 cron 表达式")
    timeout_seconds = Column(Integer, default=1800, comment="单次执行超时（秒）")
    model_override = Column(String(100), nullable=True, comment="模型覆盖")
    execution_options_json = Column(Text, nullable=True, comment="宿主平台执行选项 JSON")
    schedule_message_content = Column(Text, default="", comment="定时唤醒提示词")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class ManagedAgentCommBinding(Base):
    """宿主通讯渠道配置（1:N）"""
    __tablename__ = "managed_agent_comm_binding"

    id = Column(String(36), primary_key=True, default=_uuid)
    managed_agent_id = Column(String(36), nullable=False, index=True, comment="关联 managed_agent.id")
    provider = Column(String(30), nullable=False, comment="feishu / slack / telegram / wechat / email / webhook")
    binding_key = Column(String(200), nullable=False, comment="平台账号或连接标识")
    display_name = Column(String(100), nullable=True, comment="展示名")
    enabled = Column(Boolean, default=True, comment="是否启用")
    config_payload_encrypted = Column(Text, nullable=True, comment="加密后的平台配置")
    routing_policy_json = Column(Text, nullable=True, comment="路由策略 JSON")
    metadata_json = Column(Text, nullable=True, comment="非敏感补充信息 JSON")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class ManagedAgentBootstrapToken(Base):
    """配置态 Agent 引导 Token"""
    __tablename__ = "managed_agent_bootstrap_token"

    id = Column(String(36), primary_key=True, default=_uuid)
    managed_agent_id = Column(String(36), nullable=False, index=True, comment="关联 managed_agent.id")
    token_hash = Column(String(128), nullable=False, comment="token 的哈希值")
    purpose = Column(String(30), nullable=False, comment="download_script / register_runtime")
    scope_json = Column(Text, nullable=True, comment="附加范围信息 JSON")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    used_at = Column(DateTime, nullable=True, comment="使用时间（单次使用）")
    revoked_at = Column(DateTime, nullable=True, comment="撤销时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class ManagedAgentDeploymentSnapshot(Base):
    """部署快照，记录每次脚本生成时选择了哪些资源。"""
    __tablename__ = "managed_agent_deployment_snapshot"

    id = Column(String(36), primary_key=True, default=_uuid)
    managed_agent_id = Column(String(36), nullable=False, index=True, comment="关联 managed_agent.id")
    script_intent = Column(String(20), nullable=False, comment="bootstrap / sync")
    config_version = Column(Integer, nullable=False, comment="对应的配置版本号")
    snapshot_json = Column(Text, nullable=False, comment="本次部署的资源 ID 清单（JSON 文本）")
    status = Column(String(20), nullable=False, default="pending", comment="pending / confirmed / failed / timeout")
    failure_detail_json = Column(Text, nullable=True, comment="失败时的错误详情（JSON 文本）")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    expires_at = Column(DateTime, nullable=True, comment="超时截止时间，创建时锁定")
    confirmed_at = Column(DateTime, nullable=True, comment="确认完成时间")


class AgentRuntimePresence(Base):
    """运行态 Agent 在线状态与心跳"""
    __tablename__ = "agent_runtime_presence"

    id = Column(String(36), primary_key=True, default=_uuid)
    agent_id = Column(String(36), unique=True, nullable=False, comment="对应运行态 agent.id")
    last_heartbeat_at = Column(DateTime, nullable=True, comment="最近心跳时间")
    last_heartbeat_ip = Column(String(45), nullable=True, comment="最近心跳来源 IP")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
