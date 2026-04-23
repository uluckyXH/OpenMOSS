"""提示词服务公共导出。"""

from .agent import create_agent, delete_agent, get_agent, list_agents, update_agent
from .compose import compose_prompt, generate_onboarding
from .template import get_template, list_templates, update_template

__all__ = [
    "list_templates",
    "get_template",
    "update_template",
    "list_agents",
    "get_agent",
    "create_agent",
    "update_agent",
    "delete_agent",
    "compose_prompt",
    "generate_onboarding",
]
