"""
配置属性读取器 — 所有 @property 只读访问器
"""
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class _PropertiesConfig:
    """AppConfig 只读属性：服务、数据库、Agent、WebUI 等配置读取"""

    @property
    def is_initialized(self) -> bool:
        """是否已完成初始化向导"""
        return self._data.get("setup", {}).get("initialized", False)

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
    def database_config(self) -> dict:
        """数据库原始配置。"""
        return self._data.get("database", {})

    @property
    def database_type(self) -> str:
        """数据库类型。

        当前正式环境只落地 sqlite，但这里先统一成标准入口。
        """
        return str(self.database_config.get("type", "sqlite")).strip().lower() or "sqlite"

    @property
    def database_path(self) -> str:
        """sqlite 数据库文件路径。"""
        return str(self.database_config.get("path", "./data/tasks.db")).strip() or "./data/tasks.db"

    @property
    def database_url(self) -> str:
        """标准化数据库 URL。

        当前版本正式环境仅支持 sqlite，因此只从 `database.path`
        生成 sqlite URL，其他数据库类型后续再正式接入。
        """
        if self.database_type == "sqlite":
            if self.database_path == ":memory:":
                return "sqlite:///:memory:"
            return f"sqlite:///{self.database_path}"

        raise ValueError(f"当前版本正式环境仅支持 sqlite，暂不支持数据库类型: {self.database_type}")

    @property
    def registration_token(self) -> str:
        return self._data.get("agent", {}).get("registration_token", "")

    @property
    def allow_registration(self) -> bool:
        """Agent 自注册开关，默认开启"""
        return self._data.get("agent", {}).get("allow_registration", True)

    @property
    def workspace_root(self) -> str:
        """宿主部署机公共工作目录。

        注意：这是系统配置里声明的宿主环境共享工作目录，
        不是 OpenMOSS 服务端自己的本地目录语义。
        """
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
    def webui_github_repo(self) -> str:
        """WebUI GitHub 仓库（owner/repo 格式），用于下载 Release"""
        return self._data.get("webui", {}).get("github_repo", "uluckyXH/OpenMOSS")

    @property
    def webui_auto_update(self) -> bool:
        """是否启用 WebUI 自动更新检查"""
        return self._data.get("webui", {}).get("auto_update", True)

    @property
    def cli_version(self) -> int:
        """CLI 工具最新版本号（直接从 task-cli.py 文件读取 CLI_VERSION）"""
        import re
        # parents[2]: properties.py → app/config/ → app/ → repo root
        cli_path = Path(__file__).resolve().parents[2] / "skills" / "task-cli.py"
        try:
            content = cli_path.read_text(encoding="utf-8")
            match = re.search(r"^CLI_VERSION\s*=\s*(\d+)", content, re.MULTILINE)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return 1

    @property
    def raw(self) -> dict:
        """获取原始配置数据"""
        return self._data
