"""
OpenMOSS 应用配置包

外部代码统一通过 `from app.config import config` 获取全局配置单例。
内部结构：
  core.py        — 加载/保存/部分更新/脱敏读取
  admin.py       — 管理员密码验证与修改
  properties.py  — 所有只读 @property 访问器
  initialize.py  — 初始化向导（原子性检查+写入）
"""
from app.logging_config import configure_logging

configure_logging()

from .core import _CoreConfig
from .admin import _AdminConfig
from .properties import _PropertiesConfig
from .initialize import _InitializeConfig


class AppConfig(_CoreConfig, _AdminConfig, _PropertiesConfig, _InitializeConfig):
    """应用配置，组合所有职责模块"""
    pass


# 全局配置单例
config = AppConfig()
