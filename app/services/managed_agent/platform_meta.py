"""
managed_agent 宿主平台能力元数据。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


OPENCLAW_UI_HINTS: dict[str, Any] = {
    "host_config": {
        "description": (
            "配置此 Agent 在 OpenClaw 平台上的运行参数。公共工作目录指 OpenClaw "
            "部署机器可访问的目录，不要求 OpenMOSS 服务本机可直接访问。"
        ),
        "fields": [
            {
                "key": "host_agent_identifier",
                "label": "Agent 标识",
                "type": "text",
                "placeholder": "例如 ai-xiaohui",
                "description": "OpenClaw 中真实的 Agent ID，用于绑定运行态 Agent。",
                "required": True,
                "group": "基本",
            },
            {
                "key": "workdir_path",
                "label": "工作目录",
                "type": "text",
                "placeholder": "~/.openclaw/workspace-ai-xiaohui",
                "description": (
                    "Agent 在 OpenClaw 部署机器上的工作目录路径。主力 OpenClaw "
                    "环境可使用公共工作目录；外部远程 OpenClaw 的目录不应假设 "
                    "OpenMOSS 本机可访问。"
                ),
                "required": False,
                "group": "基本",
            },
            {
                "key": "host_config_payload",
                "label": "平台配置数据",
                "type": "textarea",
                "placeholder": '{"openclaw_config_path":"~/.openclaw/openclaw.json"}',
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
                "placeholder": '{"workspace_source":"managed"}',
                "description": "非敏感扩展信息，JSON 格式，用于前端展示或 renderer 辅助判断。",
                "required": False,
                "group": "高级",
            },
        ],
    },
    "prompt": {
        "description": (
            "定义 Agent 的系统规则、人格和身份信息。OpenClaw 渲染器会将三段内容分别映射为 "
            "AGENTS.md、SOUL.md、IDENTITY.md。"
        ),
        "render_strategies": [
            {
                "value": "host_default",
                "label": "平台默认",
                "description": "由 OpenClaw 或后端 renderer 决定最终渲染方式。",
            },
            {
                "value": "openclaw_workspace_files",
                "label": "Workspace 文件",
                "description": "渲染为 OpenClaw 工作目录文件：AGENTS.md、SOUL.md、IDENTITY.md。",
            },
            {
                "value": "openclaw_inline_schedule",
                "label": "内联 Schedule",
                "description": "将 Prompt 内容内联到定时任务唤醒消息中。",
            },
        ],
        "sections": [
            {
                "key": "system_prompt_content",
                "label": "系统提示词",
                "placeholder": "定义 Agent 的行为规则、边界和工作约束。",
                "required": True,
            },
            {
                "key": "persona_prompt_content",
                "label": "人格提示词",
                "placeholder": "定义 Agent 的沟通风格、性格和协作方式。",
                "required": False,
            },
            {
                "key": "identity_content",
                "label": "身份内容",
                "placeholder": "定义 Agent 的身份信息、职责边界和背景。",
                "required": False,
            },
        ],
    },
    "schedule": {
        "description": "配置 OpenClaw Agent 的定时唤醒任务。定时任务不是部署必填项。",
        "supported_types": ["interval", "cron"],
        "default_expr": "15m",
        "default_timeout": 1800,
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
