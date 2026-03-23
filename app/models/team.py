"""
Team Space 数据模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Team(Base):
    """团队"""
    __tablename__ = "team"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, comment="团队名称")
    description = Column(Text, default="", comment="团队描述")
    status = Column(String(20), default="active", index=True, comment="状态: active/disabled")
    team_task_id = Column(String(36), nullable=True, index=True, comment="团队初始化任务ID")
    working_dir = Column(String(500), nullable=True, comment="团队工作目录")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    profile = relationship("TeamProfile", back_populates="team", uselist=False, cascade="all, delete-orphan")


class TeamMember(Base):
    """团队成员"""
    __tablename__ = "team_member"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    self_introduction = Column(Text, default=None, comment="自我介绍内容，NULL 表示未完成")
    added_at = Column(DateTime, default=datetime.now, comment="加入时间")

    # 联合唯一索引
    __table_args__ = (
        Index("ix_team_member_team_agent", "team_id", "agent_id", unique=True),
    )

    # 关系
    team = relationship("Team", back_populates="members")


class TeamProfile(Base):
    """团队介绍文件"""
    __tablename__ = "team_profile"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("team.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    content = Column(Text, default="", comment="完整的团队介绍 markdown")
    version = Column(Integer, default=1, comment="版本号，每次更新 +1")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    team = relationship("Team", back_populates="profile")


class TeamProfileTemplate(Base):
    """介绍生成模板"""
    __tablename__ = "team_profile_template"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False, default="", comment="jinja2 模板")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    @staticmethod
    def get_default_template() -> str:
        """获取默认模板"""
        return """# {{team_name}} 团队介绍

## 团队简介
{{team_description}}

## 工作目录
{{working_dir}}

## 团队成员
{{members}}

## 角色协作配置

本团队使用 OpenClaw agent 机制实现成员间的主动通知，作为定时轮询的补充。

### 如何通知其他成员

在任务状态变化时，使用以下命令通知相关成员：

```bash
# 通知另一个 Agent（使用 openclaw agent 命令）
openclaw agent --agent <目标AgentID> --message "<通知内容>"
```

示例：
```bash
# 规划师通知执行者有新任务
openclaw agent --agent {agent_id} --message "【新任务】请前往系统认领任务：GET /api/sub-tasks/{sub_task_id}"

# 执行者通知审核者提交审核
openclaw agent --agent {agent_id} --message "【提交审核】任务ID：{sub_task_id}，请审核"
```

### 规划师 (planner)
- **职责**：分析数据、制定计划、拆分任务
- **需要通知的执行者**：请根据团队配置指定
- **通知模板**：
  ```
  【新任务通知】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  任务ID：{{task_id}}
  子任务ID：{{sub_task_id}}

  详情：{{description}}
  验收标准：{{acceptance}}

  请前往系统认领并执行：GET /api/sub-tasks/{{sub_task_id}}

  遇到问题时可通过消息渠道联系规划师。
  ```

### 执行者 (executor)
- **职责**：根据计划创作内容并发布
- **需要通知的审核者**：请根据团队配置指定
- **通知模板**：
  ```
  【任务提交审核】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  任务ID：{{task_id}}
  子任务ID：{{sub_task_id}}

  交付物：{{deliverable}}
  状态：{{from_status}} → {{to_status}}

  请前往系统审核：GET /api/sub-tasks/{{sub_task_id}}

  遇到问题时可通过消息渠道联系执行者。
  ```

### 审核者 (reviewer)
- **职责**：审核内容质量，通过或驳回
- **审核通过时通知**：巡查者（进行最终确认）
- **审核驳回时通知**：原执行者
- **通知模板**：
  ```
  【任务需要返工】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  任务ID：{{task_id}}
  子任务ID：{{sub_task_id}}

  原因：{{rejection_reason}}

  请前往系统查看详情并修复：GET /api/sub-tasks/{{sub_task_id}}

  遇到问题时可通过消息渠道联系审核者。
  ```

### 巡查者 (patrol)
- **职责**：监控系统状态、处理异常、确认任务完成
- **审核通过时通知**：确认任务状态，更新主任务进度
- **主任务全部完成时通知**：规划师（汇报整体完成情况）
- **发现异常时通知**：相关角色（根据异常类型）
- **通知模板**：
  ```
  【异常告警】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  问题：{{issue_description}}

  请及时处理：GET /api/sub-tasks/{{sub_task_id}}

  遇到问题时可通过消息渠道联系巡查者。
  ```

  【任务全部完成通知】（巡查者 → 规划师）：
  ```
  【主任务完成】

  任务：{{task_name}}
  任务ID：{{task_id}}

  所有子任务已完成，请查阅整体执行情况。

  遇到问题时可通过消息渠道联系巡查者。
  ```

### 规划师 (planner) - 被通知场景
- **执行者遇到卡点时**：执行者通知规划师请求协助
- **任务被驳回时**：审核者通知规划师（可能需要调整后续计划）
- **主任务完成时**：巡查者通知规划师整体完成情况
- **通知模板**：
  ```
  【需要关注】

  任务：{{task_name}}
  任务ID：{{task_id}}

  情况：{{situation_description}}

  请查看：GET /api/tasks/{{task_id}}

  遇到问题时可通过消息渠道联系。
  ```

## 加入我们
如需与本团队合作，请联系团队负责人。
"""
