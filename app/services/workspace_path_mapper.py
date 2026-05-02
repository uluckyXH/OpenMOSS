from __future__ import annotations

from pathlib import Path


def map_container_path_to_host(
    path: str,
    *,
    container_workspace_root: str,
    host_workspace_root: str,
) -> str:
    raw_path = str(path or "").strip()
    if not raw_path:
        return raw_path

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        return raw_path

    container_root = Path(str(container_workspace_root or "").strip() or "/workspace")
    host_root_raw = str(host_workspace_root or "").strip()
    if not host_root_raw:
        return raw_path
    host_root = Path(host_root_raw)

    try:
        relative = candidate.relative_to(container_root)
    except ValueError:
        return raw_path

    return str((host_root / relative).resolve(strict=False))


def rewrite_container_workspace_paths_in_text(
    text: str,
    *,
    container_workspace_root: str,
    host_workspace_root: str,
) -> str:
    raw_text = str(text or "")
    container_root_raw = str(container_workspace_root or "").strip() or "/workspace"
    host_root_raw = str(host_workspace_root or "").strip()
    if not raw_text or not host_root_raw:
        return raw_text
    return raw_text.replace(container_root_raw, host_root_raw)
