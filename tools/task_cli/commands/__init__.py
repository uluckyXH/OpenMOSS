"""命令域包入口。"""

from .agents import register_agent_commands
from .logs import register_log_commands
from .modules import register_module_commands
from .notifications import register_notification_commands
from .reviews import register_review_commands
from .rules import register_rules_commands
from .scores import register_score_commands
from .sub_tasks import register_sub_task_commands
from .tasks import register_task_commands

__all__ = [
    "register_agent_commands",
    "register_module_commands",
    "register_notification_commands",
    "register_review_commands",
    "register_rules_commands",
    "register_score_commands",
    "register_log_commands",
    "register_task_commands",
    "register_sub_task_commands",
]
