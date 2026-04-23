"""提示词模板管理。"""

from typing import Optional

from ._parser import TEMPLATES_DIR, VALID_ROLES, _is_valid_md


def list_templates() -> list[dict]:
    """列出所有角色模板。"""
    if not TEMPLATES_DIR.exists():
        return []

    result = []
    for path in sorted(TEMPLATES_DIR.iterdir()):
        if not _is_valid_md(path):
            continue
        role = path.stem
        if role.startswith("task-"):
            role = role[5:]
        result.append(
            {
                "role": role,
                "filename": path.name,
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return result


def get_template(role: str) -> Optional[dict]:
    """获取指定角色模板（支持 {role}.md 和 task-{role}.md 两种命名）。"""
    path = TEMPLATES_DIR / f"{role}.md"
    if not path.exists():
        path = TEMPLATES_DIR / f"task-{role}.md"
    if not path.exists():
        return None
    return {
        "role": role,
        "filename": path.name,
        "content": path.read_text(encoding="utf-8"),
    }


def update_template(role: str, content: str) -> dict:
    """更新角色模板内容。"""
    if role not in VALID_ROLES:
        raise ValueError(f"无效角色 '{role}'，可选: {', '.join(VALID_ROLES)}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMPLATES_DIR / f"{role}.md"
    path.write_text(content, encoding="utf-8")
    return {"role": role, "filename": path.name}
