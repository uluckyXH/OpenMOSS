"""
配置管理员密码职责 — 验证、修改、直接设置
"""
import bcrypt
import logging


logger = logging.getLogger(__name__)


class _AdminConfig:
    """AppConfig 密码管理：验证、修改、直接设置"""

    def verify_admin_password(self, password: str) -> bool:
        """验证管理员密码"""
        stored = self._data.get("admin", {}).get("password", "")

        if stored.startswith("bcrypt:"):
            bcrypt_hash = stored[7:]  # 去掉 "bcrypt:" 前缀
            return bcrypt.checkpw(password.encode(), bcrypt_hash.encode())

        # 兜底：不应出现，但防御性处理
        return False

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
