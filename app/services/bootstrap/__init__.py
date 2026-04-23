"""引导部署服务包。

子模块职责：
- token        — Token 生命周期（创建/校验/撤销/列表）
- register     — 运行态注册
- script_render — Bootstrap 脚本渲染
- skill_bundle — Skill Bundle 打包
- onboarding   — Onboarding 消息渲染
"""

from app.services.bootstrap.token import (
    BOOTSTRAP_PURPOSES,
    DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS,
    create_bootstrap_token,
    create_or_reissue_bootstrap_token,
    deserialize_bootstrap_scope,
    get_bootstrap_token_or_404,
    hash_bootstrap_token,
    is_bootstrap_token_valid,
    list_bootstrap_tokens,
    mark_bootstrap_token_used,
    revoke_bootstrap_token,
    serialize_bootstrap_token,
    validate_bootstrap_token,
)
from app.services.bootstrap.register import bootstrap_register
from app.services.bootstrap.script_render import render_bootstrap_script
from app.services.bootstrap.skill_bundle import (
    build_skill_bundle_zip,
    build_skill_bundle_zip_for_managed_agent,
    build_skill_bundle_zip_for_runtime_agent,
    get_skill_bundle_dir_name,
    render_skill_bundle_layout,
    render_task_cli_launcher,
)
from app.services.bootstrap.onboarding import render_curl_command, render_onboarding_message

__all__ = [
    # token
    "BOOTSTRAP_PURPOSES",
    "DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS",
    "create_bootstrap_token",
    "create_or_reissue_bootstrap_token",
    "deserialize_bootstrap_scope",
    "get_bootstrap_token_or_404",
    "hash_bootstrap_token",
    "is_bootstrap_token_valid",
    "list_bootstrap_tokens",
    "mark_bootstrap_token_used",
    "revoke_bootstrap_token",
    "serialize_bootstrap_token",
    "validate_bootstrap_token",
    # register
    "bootstrap_register",
    # script_render
    "render_bootstrap_script",
    # skill_bundle
    "build_skill_bundle_zip",
    "build_skill_bundle_zip_for_managed_agent",
    "build_skill_bundle_zip_for_runtime_agent",
    "get_skill_bundle_dir_name",
    "render_skill_bundle_layout",
    "render_task_cli_launcher",
    # onboarding
    "render_curl_command",
    "render_onboarding_message",
]
