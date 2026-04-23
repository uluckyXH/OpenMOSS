"""提示词文件内部解析工具。"""

import re
from pathlib import Path
from typing import Optional

import frontmatter


BASE_DIR = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = BASE_DIR / "prompts" / "templates"
AGENTS_DIR = BASE_DIR / "prompts" / "agents"

VALID_ROLES = {"planner", "executor", "reviewer", "patrol"}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitkeep"}
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]*$")


def _is_valid_md(path: Path) -> bool:
    """判断是否为合法的 .md 文件（排除垃圾文件和非 .md）。"""
    return path.is_file() and path.suffix == ".md" and path.name not in IGNORED_FILES


def _parse_prompt_file(path: Path) -> dict:
    """解析单个提示词文件，返回元数据 + 内容。"""
    post = frontmatter.load(str(path))
    slug = path.stem

    meta = {
        "slug": slug,
        "filename": path.name,
        "name": post.get("name", ""),
        "role": post.get("role", ""),
        "description": post.get("description", ""),
        "created_at": str(post.get("created_at", "")),
        "example": bool(post.get("example", False)),
        "content": post.content,
        "has_frontmatter": bool(post.metadata),
    }

    if not post.metadata:
        meta["status"] = "unconfigured"
    elif meta["role"] and not slug.startswith(meta["role"] + "-"):
        meta["status"] = "rename_suggested"
    else:
        meta["status"] = "ok"

    return meta


def _validate_slug(slug: str) -> Optional[str]:
    """校验 slug 合法性，返回错误信息或 None。"""
    if not slug:
        return "slug 不能为空"
    if not SLUG_PATTERN.match(slug):
        return "slug 只允许小写英文、数字和短横线，且不能以短横线开头"
    return None
