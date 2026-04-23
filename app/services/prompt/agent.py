"""Agent Prompt 文件管理。"""

from datetime import date
from typing import Optional

import frontmatter

from ._parser import AGENTS_DIR, VALID_ROLES, _is_valid_md, _parse_prompt_file, _validate_slug


def list_agents() -> list[dict]:
    """列出所有 Agent 提示词（扫描 prompts/agents/ 目录）。"""
    if not AGENTS_DIR.exists():
        return []

    result = []
    for path in sorted(AGENTS_DIR.iterdir()):
        if not _is_valid_md(path):
            continue
        try:
            meta = _parse_prompt_file(path)
            meta.pop("content", None)
            result.append(meta)
        except Exception:
            continue
    return result


def get_agent(slug: str) -> Optional[dict]:
    """获取 Agent 提示词详情。"""
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        return None
    return _parse_prompt_file(path)


def create_agent(
    slug: str,
    name: str,
    role: str,
    description: str,
    content: str,
) -> dict:
    """新建 Agent 提示词。"""
    if role not in VALID_ROLES:
        raise ValueError(f"无效角色 '{role}'，可选: {', '.join(VALID_ROLES)}")

    full_slug = f"{role}-{slug}" if not slug.startswith(role + "-") else slug
    err = _validate_slug(full_slug)
    if err:
        raise ValueError(err)

    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = AGENTS_DIR / f"{full_slug}.md"
    if path.exists():
        raise ValueError(f"文件 '{full_slug}.md' 已存在，请更换名称")

    post = frontmatter.Post(content)
    post["name"] = name
    post["role"] = role
    post["description"] = description
    post["created_at"] = str(date.today())

    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return {"slug": full_slug, "filename": path.name}


def update_agent(
    slug: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
) -> dict:
    """编辑 Agent 提示词（支持重命名）。"""
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        raise ValueError(f"文件 '{slug}.md' 不存在")

    post = frontmatter.load(str(path))

    if name is not None:
        post["name"] = name
    if role is not None:
        if role not in VALID_ROLES:
            raise ValueError(f"无效角色 '{role}'，可选: {', '.join(VALID_ROLES)}")
        post["role"] = role
    if description is not None:
        post["description"] = description
    if content is not None:
        post.content = content

    if "created_at" not in post.metadata:
        post["created_at"] = str(date.today())

    new_role = post.get("role", "")
    new_slug = slug

    if new_role and not slug.startswith(new_role + "-"):
        base_name = slug
        for known_role in VALID_ROLES:
            if slug.startswith(known_role + "-"):
                base_name = slug[len(known_role) + 1 :]
                break
        new_slug = f"{new_role}-{base_name}"

        new_path = AGENTS_DIR / f"{new_slug}.md"
        if new_path.exists() and new_path != path:
            raise ValueError(f"重命名目标 '{new_slug}.md' 已存在")

        new_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        if new_path != path:
            path.unlink()
    else:
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    return {"slug": new_slug, "filename": f"{new_slug}.md"}


def delete_agent(slug: str) -> bool:
    """删除 Agent 提示词。"""
    path = AGENTS_DIR / f"{slug}.md"
    if not path.exists():
        raise ValueError(f"文件 '{slug}.md' 不存在")
    path.unlink()
    return True
