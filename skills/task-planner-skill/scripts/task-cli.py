#!/usr/bin/env python3
"""task-planner-skill 兼容入口。

优先使用同目录下分发的 `task_cli` 共享实现。
若当前仍在仓库开发态且本地 Skill 包源码尚未注入，则回退到 `skills/task-cli.py`。
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    try:
        from task_cli.app import run_default_cli
    except ImportError:
        run_default_cli = None

    if run_default_cli is not None:
        run_default_cli(script_path=__file__)
        return 0

    legacy_entry = Path(__file__).resolve().parents[2] / "task-cli.py"
    if legacy_entry.exists():
        sys.argv[0] = str(legacy_entry)
        runpy.run_path(str(legacy_entry), run_name="__main__")
        return 0
    print("未找到可用的 task-cli 入口，请检查 Skill 包是否完整。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
