"""
WebUI 前端自动更新服务

负责从 GitHub Release 检查、下载和部署 WebUI 前端静态文件。
支持升级和回滚（当版本被标记为 pre-release 时自动降级到安全版本）。
"""
import asyncio
import json
import os
import shutil
import tarfile
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class UpdateCheckResult:
    """版本检查结果"""
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    update_available: bool = False
    update_type: str = "none"  # "none" | "upgrade" | "rollback"
    checked_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "update_type": self.update_type,
            "checked_at": self.checked_at,
            "error": self.error,
        }


def _parse_version(version_str: str) -> tuple[int, ...]:
    """解析语义化版本号为可比较的元组"""
    try:
        return tuple(int(x) for x in version_str.strip().split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)


class WebUIUpdater:
    """WebUI 前端自动更新服务"""

    CHECK_COOLDOWN = 1800  # 30 分钟 cooldown
    DOWNLOAD_TIMEOUT = 120  # 下载超时 120 秒
    MANIFEST_TIMEOUT = 15  # manifest 下载超时 15 秒

    def __init__(self):
        self._static_dir: Optional[Path] = None
        self._github_repo: Optional[str] = None
        self._auto_update: bool = True
        self._last_check: Optional[UpdateCheckResult] = None
        self._last_check_time: float = 0
        self._update_lock = threading.Lock()
        self._updating = False

    def _get_static_dir(self) -> Path:
        """获取 static 目录路径"""
        if self._static_dir is None:
            self._static_dir = Path(__file__).resolve().parent.parent.parent / "static"
        return self._static_dir

    def _get_github_repo(self) -> str:
        """获取 GitHub 仓库配置"""
        if self._github_repo is None:
            from app.config import config
            self._github_repo = config.webui_github_repo
        return self._github_repo

    def _is_auto_update_enabled(self) -> bool:
        """获取自动更新开关"""
        from app.config import config
        return config.webui_auto_update

    async def _get_webui_release_base_url(self) -> str:
        """获取 WebUI Release 的下载 URL

        通过 GitHub API 查找最新的 webui-v* tag 的 Release，
        避免被后端版本的 Release（v1.x.x）顶掉 latest 指向。
        如果 API 查询失败，回退到 releases/latest/download。
        """
        repo = self._get_github_repo()
        fallback = f"https://github.com/{repo}/releases/latest/download"

        try:
            api_url = f"https://api.github.com/repos/{repo}/releases"
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.MANIFEST_TIMEOUT,
            ) as client:
                resp = await client.get(api_url, headers={"Accept": "application/vnd.github+json"})
                resp.raise_for_status()
                releases = resp.json()

            # 找最新的 webui-v* tag 的已发布 Release
            for release in releases:
                tag = release.get("tag_name", "")
                if tag.startswith("webui-v") and not release.get("draft") and not release.get("prerelease"):
                    return f"https://github.com/{repo}/releases/download/{tag}"

            print("[WebUI Updater] 未找到 webui-v* Release，回退到 latest")
            return fallback

        except Exception as e:
            print(f"[WebUI Updater] GitHub API 查询失败: {e}，回退到 latest")
            return fallback

    def get_current_version(self) -> Optional[str]:
        """读取当前安装的 WebUI 版本（从 static/webui-manifest.json）"""
        manifest_path = self._get_static_dir() / "webui-manifest.json"
        try:
            if manifest_path.exists():
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                return data.get("version")
        except Exception:
            pass
        return None

    def is_webui_available(self) -> bool:
        """检查 WebUI 前端是否可用"""
        static_dir = self._get_static_dir()
        return (static_dir / "index.html").is_file()

    async def check_for_update(self, force: bool = False) -> UpdateCheckResult:
        """检查是否有 WebUI 更新

        Args:
            force: 是否强制检查（忽略 cooldown）

        Returns:
            UpdateCheckResult 包含版本信息和更新状态
        """
        now = time.time()

        # cooldown 检查（除非 force）
        if (
            not force
            and self._last_check is not None
            and (now - self._last_check_time) < self.CHECK_COOLDOWN
        ):
            return self._last_check

        current_version = self.get_current_version()
        result = UpdateCheckResult(current_version=current_version)

        # 如果自动更新关闭，只返回当前版本
        if not self._is_auto_update_enabled():
            result.checked_at = _iso_now()
            self._last_check = result
            self._last_check_time = now
            return result

        # 从 GitHub 下载 manifest
        try:
            base_url = await self._get_webui_release_base_url()
            manifest_url = f"{base_url}/webui-manifest.json"

            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.MANIFEST_TIMEOUT,
            ) as client:
                resp = await client.get(manifest_url)
                resp.raise_for_status()
                remote_manifest = resp.json()
                latest_version = remote_manifest.get("version")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                result.error = "未找到 WebUI Release（GitHub 上可能还没有发布）"
            else:
                result.error = f"检查更新失败: HTTP {e.response.status_code}"
            result.checked_at = _iso_now()
            self._last_check = result
            self._last_check_time = now
            return result
        except Exception as e:
            result.error = f"检查更新失败: {e}"
            result.checked_at = _iso_now()
            self._last_check = result
            self._last_check_time = now
            return result

        result.latest_version = latest_version
        result.checked_at = _iso_now()

        # 版本比较
        if current_version and latest_version:
            current = _parse_version(current_version)
            latest = _parse_version(latest_version)

            if latest > current:
                result.update_available = True
                result.update_type = "upgrade"
            elif latest < current:
                # 远端版本低于本地 → 当前版本被撤回（标记为 pre-release）
                result.update_available = True
                result.update_type = "rollback"
            else:
                result.update_type = "none"
        elif not current_version and latest_version:
            # 本地无版本信息但有前端文件，或无前端文件
            result.update_available = True
            result.update_type = "upgrade"

        self._last_check = result
        self._last_check_time = now
        return result

    async def download_and_apply(self) -> dict:
        """下载并部署最新版本的 WebUI

        Returns:
            dict: {"success": bool, "message": str, "version": str | None}
        """
        if not self._update_lock.acquire(blocking=False):
            return {
                "success": False,
                "message": "另一个更新正在进行中",
                "version": self.get_current_version(),
            }

        self._updating = True
        try:
            return await self._do_download_and_apply()
        finally:
            self._updating = False
            self._update_lock.release()

    async def _do_download_and_apply(self) -> dict:
        """实际执行下载和部署"""
        static_dir = self._get_static_dir()
        backup_dir = static_dir.parent / "static.bak"

        try:
            base_url = await self._get_webui_release_base_url()
            tar_url = f"{base_url}/webui-dist.tar.gz"

            print(f"[WebUI Updater] 开始下载: {tar_url}")

            # 1. 下载 tar.gz 到临时文件
            temp_dir = await asyncio.to_thread(tempfile.mkdtemp)
            tar_path = os.path.join(temp_dir, "webui-dist.tar.gz")

            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=self.DOWNLOAD_TIMEOUT,
                ) as client:
                    resp = await client.get(tar_url)
                    resp.raise_for_status()

                    await asyncio.to_thread(
                        _write_bytes, tar_path, resp.content
                    )

                print(f"[WebUI Updater] 下载完成: {len(resp.content)} bytes")

                # 2. 备份当前 static/ 目录
                await asyncio.to_thread(
                    _backup_static, static_dir, backup_dir
                )

                # 3. 解压到 static/
                await asyncio.to_thread(
                    _extract_tar, tar_path, static_dir
                )

                # 4. 验证 index.html 存在
                if not (static_dir / "index.html").is_file():
                    raise RuntimeError("解压后未找到 index.html")

                new_version = self.get_current_version()
                print(f"[WebUI Updater] ✅ 更新完成: {new_version}")

                # 5. 清理备份
                await asyncio.to_thread(_remove_dir, backup_dir)

                # 6. 重置缓存，下次会重新检查
                self._last_check = None
                self._last_check_time = 0

                return {
                    "success": True,
                    "message": f"WebUI 已更新到 {new_version}",
                    "version": new_version,
                }

            finally:
                # 清理临时目录
                await asyncio.to_thread(_remove_dir, temp_dir)

        except Exception as e:
            print(f"[WebUI Updater] ❌ 更新失败: {e}")

            # 恢复备份
            if backup_dir.is_dir():
                print("[WebUI Updater] 正在从备份恢复...")
                await asyncio.to_thread(_restore_backup, static_dir, backup_dir)

            return {
                "success": False,
                "message": f"更新失败: {e}",
                "version": self.get_current_version(),
            }

    async def ensure_webui_exists(self) -> None:
        """确保 WebUI 前端文件存在（启动时调用）

        如果 static/index.html 不存在，从 GitHub Release 下载最新版。
        """
        if self.is_webui_available():
            version = self.get_current_version()
            if version:
                print(f"[WebUI] 前端版本: {version}")
            return

        if not self._is_auto_update_enabled():
            print("[WebUI] ⚠️  未找到前端文件且自动更新已关闭")
            print("[WebUI]    API 正常运行，但 WebUI 不可用")
            return

        print("[WebUI] 未找到前端文件，正在从 GitHub Release 下载...")

        result = await self.download_and_apply()
        if result["success"]:
            print(f"[WebUI] ✅ 前端已自动部署: v{result['version']}")
        else:
            print(f"[WebUI] ⚠️  自动部署失败: {result['message']}")
            print("[WebUI]    API 正常运行，但 WebUI 不可用")
            print("[WebUI]    可稍后通过管理端手动触发更新")

    @property
    def is_updating(self) -> bool:
        """是否正在更新中"""
        return self._updating


def _iso_now() -> str:
    """返回 ISO 格式的当前时间"""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _write_bytes(path: str, data: bytes) -> None:
    """写入二进制文件"""
    with open(path, "wb") as f:
        f.write(data)


def _backup_static(static_dir: Path, backup_dir: Path) -> None:
    """备份 static 目录"""
    if backup_dir.is_dir():
        shutil.rmtree(backup_dir)
    if static_dir.is_dir():
        shutil.copytree(static_dir, backup_dir)
        print(f"[WebUI Updater] 已备份当前版本到 {backup_dir}")


def _extract_tar(tar_path: str, target_dir: Path) -> None:
    """解压 tar.gz 到目标目录"""
    # 先清空目标目录
    if target_dir.is_dir():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_path, "r:gz") as tar:
        # 安全检查：防止路径穿越
        for member in tar.getmembers():
            member_path = os.path.join(str(target_dir), member.name)
            abs_target = os.path.abspath(str(target_dir))
            abs_member = os.path.abspath(member_path)
            if not abs_member.startswith(abs_target):
                raise RuntimeError(f"危险路径: {member.name}")
        tar.extractall(path=str(target_dir))

    print(f"[WebUI Updater] 已解压到 {target_dir}")


def _restore_backup(static_dir: Path, backup_dir: Path) -> None:
    """从备份恢复 static 目录"""
    if static_dir.is_dir():
        shutil.rmtree(static_dir)
    if backup_dir.is_dir():
        shutil.copytree(backup_dir, static_dir)
        shutil.rmtree(backup_dir)
        print("[WebUI Updater] 已从备份恢复")


def _remove_dir(path) -> None:
    """安全删除目录"""
    path = Path(path)
    if path.is_dir():
        shutil.rmtree(path)


# 全局单例
webui_updater = WebUIUpdater()
