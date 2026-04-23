"""
配置核心 — AppConfig 基础职责：加载、保存、部分更新、脱敏读取
"""
import logging
import os
import bcrypt
import yaml
import threading
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class _CoreConfig:
    """AppConfig 核心：文件 I/O、部分更新、脱敏导出"""

    def __init__(self, config_path: Optional[str] = None):
        resolved_config_path = config_path or os.getenv("OPENMOSS_CONFIG") or "config.yaml"
        self.config_path = Path(resolved_config_path)
        self._data = {}
        self._lock = threading.RLock()  # 可重入锁，防止内部方法嵌套调用时死锁
        self.load()

    def load(self):
        """加载配置文件"""
        if not self.config_path.exists():
            example_path = Path("config.example.yaml")
            if example_path.exists():
                import shutil
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(example_path, self.config_path)
                logger.info("已从 %s 创建配置文件 %s", example_path, self.config_path)
            else:
                raise FileNotFoundError(
                    f"配置文件 {self.config_path} 不存在，请从 config.example.yaml 复制"
                )

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

        # 启动时自动加密管理员密码
        self._auto_encrypt_password()

    def _auto_encrypt_password(self):
        """如果密码是明文或旧的 MD5 格式，自动升级为 bcrypt 并回写配置文件"""
        admin = self._data.get("admin", {})
        password = str(admin.get("password", ""))

        if not password:
            return

        if password.startswith("bcrypt:"):
            return

        if password.startswith("md5:"):
            logger.warning("检测到旧的 MD5 密码格式，自动升级为 bcrypt（使用默认密码 admin123）")
            logger.warning("请登录后立即修改管理员密码！")
            raw_password = "admin123"
        else:
            raw_password = password

        hashed = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()
        admin["password"] = f"bcrypt:{hashed}"
        self._data["admin"] = admin

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

        logger.info("管理员密码已加密为 bcrypt")

    def _save(self):
        """将当前配置数据回写到 YAML 文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def update(self, data: dict):
        """部分更新配置（合并更新 + 回写 YAML）

        支持的顶级 key：project, agent, notification, webui, workspace, server
        server 下仅允许更新 external_url（port/host 需手动改 config.yaml 后重启）
        不支持更新：setup, admin.password, database
        """
        ALLOWED_KEYS = {"project", "agent", "notification", "webui", "workspace", "server"}
        SERVER_ALLOWED_SUBKEYS = {"external_url"}

        with self._lock:
            for key, value in data.items():
                if key not in ALLOWED_KEYS:
                    raise ValueError(f"不允许更新配置项: {key}")
                if key == "server" and isinstance(value, dict):
                    for sub_key in value:
                        if sub_key not in SERVER_ALLOWED_SUBKEYS:
                            raise ValueError(f"不允许通过 API 更新 server.{sub_key}，请手动修改 config.yaml")
                if isinstance(value, dict) and isinstance(self._data.get(key), dict):
                    self._data[key].update(value)
                else:
                    self._data[key] = value

            self._save()

    def get_safe_config(self) -> dict:
        """获取脱敏后的配置（密码/令牌等替换为 ***）"""
        import copy
        safe = copy.deepcopy(self._data)

        if "admin" in safe:
            safe["admin"]["password"] = "***"
        if "agent" in safe:
            safe["agent"]["registration_token"] = safe["agent"].get("registration_token", "")

        safe.pop("setup", None)

        return safe
