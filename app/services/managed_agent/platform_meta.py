"""
managed_agent 宿主平台能力元数据。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


OPENCLAW_UI_HINTS: dict[str, Any] = {
    "host_config": {
        "description": "配置此 Agent 在 OpenClaw 平台上的运行参数。",
        "fields": [
            {
                "key": "host_agent_identifier",
                "label": "Agent ID",
                "type": "text",
                "placeholder": "content-executor-01",
                "description": (
                    "OpenClaw 中的系统唯一标识。仅限英文小写字母、数字、下划线和连字符"
                    "（a-z 0-9 _ -），首字符为字母或数字，最长 64 位。合法示例："
                    "content-executor-01、review-agent-01。"
                ),
                "required": True,
                "group": "基本",
            },
            {
                "key": "workdir_path",
                "label": "工作空间（Workspace）",
                "type": "text",
                "placeholder": "~/.openclaw/workspace-{Agent ID}",
                "description": (
                    "Agent 的专属文件空间，也是默认的文件操作目录，用于存放提示词"
                    "（AGENTS.md/SOUL.md）、记忆、技能和任务产出。通常为 "
                    "~/.openclaw/workspace-{Agent ID}，留空时将根据 Agent ID 自动生成。"
                ),
                "required": False,
                "group": "基本",
            },
            {
                "key": "host_config_payload",
                "label": "平台配置数据",
                "type": "textarea",
                "description": (
                    "除标准字段外的宿主平台扩展配置。留空表示不修改现有值；输入新内容会替换旧值，"
                    "保存后仅返回脱敏结果。"
                ),
                "required": False,
                "sensitive": True,
                "group": "高级",
            },
            {
                "key": "host_metadata_json",
                "label": "扩展元数据",
                "type": "json",
                "placeholder": "{}",
                "description": "平台侧的额外元数据，JSON 格式。",
                "required": False,
                "group": "高级",
            },
        ],
    },
    "prompt": {
        "description": (
            "定义 Agent 在 OpenClaw Workspace 中的工作规则、人格设定和身份信息。"
            "这些内容都是可选配置，保存后会渲染为 AGENTS.md、SOUL.md、IDENTITY.md。"
        ),
        "render_strategies": [
            {
                "value": "openclaw_workspace_files",
                "label": "Workspace 文件",
                "description": "渲染为 OpenClaw Workspace 文件：AGENTS.md、SOUL.md、IDENTITY.md。",
                "is_default": True,
            },
        ],
        "sections": [
            {
                "key": "system_prompt_content",
                "label": "工作规则（AGENTS.md）",
                "placeholder": "填写 Agent 的工作流程、工具使用规则和协作约束。",
                "required": False,
                "description": "定义 Agent 的工作规则和执行流程。",
                "detail": (
                    "对应 OpenClaw Workspace 中的 AGENTS.md。用于描述 Agent 的操作手册，"
                    "包括工作流程、安全边界、工具使用规则、记忆策略和协作约束。"
                    "这是最核心的行为规则文件，可根据实际情况决定是否添加或修改。"
                ),
            },
            {
                "key": "persona_prompt_content",
                "label": "人格设定（SOUL.md）",
                "placeholder": "填写 Agent 的性格、语气和沟通风格。",
                "required": False,
                "description": "定义 Agent 的性格和说话风格。",
                "detail": (
                    "对应 OpenClaw Workspace 中的 SOUL.md。用于描述 Agent 的语气、态度、"
                    "个性和与用户的关系边界，决定 Agent 是偏工具化还是更有独立个性。"
                ),
            },
            {
                "key": "identity_content",
                "label": "身份信息（IDENTITY.md）",
                "placeholder": "填写 Agent 的名称、外显身份和展示信息。",
                "required": False,
                "description": "定义 Agent 的名称和外显身份。",
                "detail": (
                    "对应 OpenClaw Workspace 中的 IDENTITY.md。用于描述 Agent 的名字、emoji、"
                    "头像等对外展示信息，比人格设定更轻量，主要用于标识而非行为规则。"
                ),
            },
        ],
    },
    "schedule": {
        "description": "配置 OpenClaw Agent 的定时唤醒任务。定时任务不是部署必填项，但一旦创建就应一次性提交完整配置。",
        "supported_types": ["interval", "cron"],
        "default_expr": "15m",
        "default_timeout": 1800,
        "required_fields": [
            "schedule_type",
            "schedule_expr",
            "timeout_seconds",
            "schedule_message_content",
        ],
        "expr_help": {
            "interval": "间隔格式：数字 + 单位，单位支持 s/m/h/d，例如 15m、1h、2d。",
            "cron": "cron 格式：标准 5 段表达式，例如 0 9 * * *。",
        },
        "message_label": "定时唤醒提示词",
    },
    "comm": {
        "description": "配置宿主平台侧通讯渠道。当前后端只落地 Feishu，其他 provider 仍是预留枚举。",
    },
    "bootstrap": {
        "description": "生成 OpenClaw 接入脚本、注册 token 和 skill-bundle 下载入口。",
        "deploy_guide": "将生成的脚本复制到 OpenClaw 部署机器执行，完成 Agent 文件写入和运行态注册。",
        "onboarding_guide": "接入说明会生成带一次性 bootstrap token 的 curl 命令，token 过期后需要重新生成。",
    },
}


HOST_PLATFORM_META: dict[str, dict[str, Any]] = {
    "openclaw": {
        "key": "openclaw",
        "label": "OpenClaw",
        "description": "OpenClaw Agent 平台，当前 OpenMOSS 已落地支持的首个宿主平台。",
        "access_modes": ["local", "remote"],
        "deployment_modes": ["create_sub_agent", "bind_existing_agent", "bind_main_agent"],
        "capabilities": {
            "renderer": True,
            "bootstrap_script": True,
            "skill_bundle": True,
            "prompt_preview": True,
            "schedule": True,
            "comm_binding": True,
        },
        "supported_comm_providers": ["feishu"],
        "ui_hints": OPENCLAW_UI_HINTS,
    },
}


def list_supported_host_platforms() -> list[dict[str, Any]]:
    """返回当前后端真实支持的宿主平台能力。"""
    return [deepcopy(HOST_PLATFORM_META[key]) for key in sorted(HOST_PLATFORM_META.keys())]
