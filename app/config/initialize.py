"""
配置初始化向导职责 — 原子性初始化检查与写入
"""
import logging


logger = logging.getLogger(__name__)


class _InitializeConfig:
    """AppConfig 初始化向导：标记完成状态、执行原子性初始化"""

    def mark_initialized(self):
        """标记初始化完成（使用 RLock，可安全嵌套调用）"""
        with self._lock:
            if "setup" not in self._data:
                self._data["setup"] = {}
            self._data["setup"]["initialized"] = True
            self._save()

    def initialize(self, data: dict):
        """初始化向导：原子性地检查 + 写入配置项

        在锁内检查 is_initialized，确保不会并发重复初始化。
        如果已初始化，返回 False；成功初始化返回 True。
        """
        with self._lock:
            # 原子性检查（防止并发竞态）
            if self.is_initialized:
                return False

            # 设置密码
            password = data.get("admin_password")
            if password:
                self.set_password(password)

            # 设置项目名
            if data.get("project_name"):
                if "project" not in self._data:
                    self._data["project"] = {}
                self._data["project"]["name"] = data["project_name"]

            # 设置工作目录
            if data.get("workspace_root"):
                if "workspace" not in self._data:
                    self._data["workspace"] = {}
                self._data["workspace"]["root"] = data["workspace_root"]

            # 设置注册令牌
            if "agent" not in self._data:
                self._data["agent"] = {}
            if data.get("registration_token"):
                self._data["agent"]["registration_token"] = data["registration_token"]
            else:
                import secrets
                self._data["agent"]["registration_token"] = secrets.token_hex(16)

            if "allow_registration" in data:
                self._data["agent"]["allow_registration"] = data["allow_registration"]

            # 设置通知
            if data.get("notification"):
                self._data["notification"] = data["notification"]

            # 设置服务外网地址
            if data.get("external_url"):
                if "server" not in self._data:
                    self._data["server"] = {}
                self._data["server"]["external_url"] = data["external_url"]

            # 标记初始化完成
            self.mark_initialized()
            return True
