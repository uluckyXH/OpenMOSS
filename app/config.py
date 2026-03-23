"""
OpenMOSS 任务调度中间件 — 配置加载模块
"""
import os
import bcrypt
import uvicorn
import yaml
import threading
from pathlib import Path
from typing import Optional


class AppConfig:
    """应用配置"""

    def __init__(self, config_path: str = None):
        # 动态计算项目根目录（config.py 位于 app/ 目录下）
        if config_path is None:
            # 基于 config.py 的位置推导项目根目录
            module_dir = Path(__file__).resolve().parent  # app/
            project_root = module_dir.parent  # 项目根目录
            config_path = project_root / "config.yaml"
            example_path = project_root / "config.example.yaml"
        else:
            config_path = Path(config_path)
            example_path = config_path.parent / "config.example.yaml"

        self.config_path = config_path
        self.example_path = example_path
        self._data = {}
        self._lock = threading.RLock()  # 可重入锁，防止内部方法嵌套调用时死锁
        self.load()

    def load(self):
        """加载配置文件"""
        if not self.config_path.exists():
            # 如果没有 config.yaml，从模板复制
            if self.example_path.exists():
                import shutil
                shutil.copy(self.example_path, self.config_path)
                print(f"[Config] 已从 {self.example_path} 创建配置文件 {self.config_path}")
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
            # 已经是 bcrypt 格式，无需处理
            return

        if password.startswith("md5:"):
            # 旧的 MD5 格式，无法反向解密，需要用户重新设置密码
            # 使用默认密码 admin123 重新加密
            print(f"[Config] ⚠️ 检测到旧的 MD5 密码格式，自动升级为 bcrypt（使用默认密码 admin123）")
            print(f"[Config] ⚠️ 请登录后立即修改管理员密码！")
            raw_password = "admin123"
        else:
            # 明文密码
            raw_password = password

        # 用 bcrypt 加密
        hashed = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()
        admin["password"] = f"bcrypt:{hashed}"
        self._data["admin"] = admin

        # 回写配置文件
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

        print(f"[Config] 管理员密码已加密为 bcrypt")

    def _save(self):
        """将当前配置数据回写到 YAML 文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def verify_admin_password(self, password: str) -> bool:
        """验证管理员密码"""
        stored = self._data.get("admin", {}).get("password", "")

        if stored.startswith("bcrypt:"):
            bcrypt_hash = stored[7:]  # 去掉 "bcrypt:" 前缀
            return bcrypt.checkpw(password.encode(), bcrypt_hash.encode())

        # 兜底：不应出现，但防御性处理
        return False

    @property
    def is_initialized(self) -> bool:
        """是否已完成初始化向导"""
        return self._data.get("setup", {}).get("initialized", False)

    def mark_initialized(self):
        """标记初始化完成（使用 RLock，可安全嵌套调用）"""
        with self._lock:
            if "setup" not in self._data:
                self._data["setup"] = {}
            self._data["setup"]["initialized"] = True
            self._save()

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
                # server 下做子字段白名单校验
                if key == "server" and isinstance(value, dict):
                    for sub_key in value:
                        if sub_key not in SERVER_ALLOWED_SUBKEYS:
                            raise ValueError(f"不允许通过 API 更新 server.{sub_key}，请手动修改 config.yaml")
                if isinstance(value, dict) and isinstance(self._data.get(key), dict):
                    self._data[key].update(value)
                else:
                    self._data[key] = value

            self._save()

    def update_password(self, old_password: str, new_password: str):
        """修改管理员密码（需验证旧密码）"""
        with self._lock:
            if not self.verify_admin_password(old_password):
                raise ValueError("旧密码验证失败")

            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            if "admin" not in self._data:
                self._data["admin"] = {}
            self._data["admin"]["password"] = f"bcrypt:{hashed}"
            self._save()

    def set_password(self, new_password: str):
        """直接设置新密码（跳过旧密码验证，用于初始化向导，调用方需持有锁）"""
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        if "admin" not in self._data:
            self._data["admin"] = {}
        self._data["admin"]["password"] = f"bcrypt:{hashed}"
        self._save()

    def get_safe_config(self) -> dict:
        """获取脱敏后的配置（密码/令牌等替换为 ***）"""
        import copy
        safe = copy.deepcopy(self._data)

        # 脱敏
        if "admin" in safe:
            safe["admin"]["password"] = "***"
        if "agent" in safe:
            safe["agent"]["registration_token"] = safe["agent"].get("registration_token", "")

        # 排除内部标记
        safe.pop("setup", None)

        return safe

    @property
    def server_port(self) -> int:
        return self._data.get("server", {}).get("port", 6565)

    @property
    def server_host(self) -> str:
        return self._data.get("server", {}).get("host", "0.0.0.0")

    @property
    def server_external_url(self) -> str:
        """外网访问地址（用于 Agent 工具下载和对接）

        如果未配置，兜底用 host:port 拼接（通常不可从外网访问）。
        旧版部署无此字段时自动兜底，不会报错。
        """
        url = self._data.get("server", {}).get("external_url", "")
        if not url:
            host = self.server_host
            if host == "0.0.0.0":
                host = "127.0.0.1"  # 0.0.0.0 不是有效访问地址，兜底用 localhost
            return f"http://{host}:{self.server_port}"
        return url.rstrip("/")

    @property
    def has_external_url(self) -> bool:
        """外网地址是否已配置（非空）"""
        return bool(self._data.get("server", {}).get("external_url", ""))

    @property
    def database_path(self) -> str:
        return self._data.get("database", {}).get("path", "./data/tasks.db")

    @property
    def database_type(self) -> str:
        return self._data.get("database", {}).get("type", "sqlite")

    @property
    def registration_token(self) -> str:
        return self._data.get("agent", {}).get("registration_token", "")

    @property
    def allow_registration(self) -> bool:
        """Agent 自注册开关，默认开启"""
        return self._data.get("agent", {}).get("allow_registration", True)

    @property
    def workspace_root(self) -> str:
        return self._data.get("workspace", {}).get("root", "./workspace")

    @property
    def project_name(self) -> str:
        return self._data.get("project", {}).get("name", "OpenMOSS")

    @property
    def notification_config(self) -> dict:
        return self._data.get("notification", {})

    @property
    def public_feed_enabled(self) -> bool:
        """活动流展示页是否公开"""
        return self._data.get("webui", {}).get("public_feed", False)

    @property
    def feed_retention_days(self) -> int:
        """请求日志保留天数"""
        return self._data.get("webui", {}).get("feed_retention_days", 7)

    @property
    def cli_version(self) -> int:
        """CLI 工具最新版本号（task-cli.py 自更新用）"""
        return self._data.get("cli", {}).get("version", 1)

    @property
    def raw(self) -> dict:
        """获取原始配置数据"""
        return self._data

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
                # 自动生成随机令牌
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


# 全局配置实例
config = AppConfig()
