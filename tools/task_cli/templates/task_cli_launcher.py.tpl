#!/usr/bin/env python3
"""Agent 专属 task-cli 入口。"""

from __future__ import annotations

import sys
from pathlib import Path


BASE_URL = ${BASE_URL_LITERAL}
CLI_VERSION = ${CLI_VERSION_LITERAL}
DEFAULT_API_KEY = ${DEFAULT_API_KEY_LITERAL}
AGENT_ID = ${AGENT_ID_LITERAL}
AGENT_NAME = ${AGENT_NAME_LITERAL}
AGENT_ROLE = ${AGENT_ROLE_LITERAL}
CLI_PROFILE = ${CLI_PROFILE_LITERAL}


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    from task_cli.app import run_skill_cli

    run_skill_cli(
        script_path=__file__,
        base_url=BASE_URL,
        cli_version=CLI_VERSION,
        default_api_key=DEFAULT_API_KEY,
        agent_id=AGENT_ID,
        agent_name=AGENT_NAME,
        agent_role=AGENT_ROLE,
        cli_profile=CLI_PROFILE,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
