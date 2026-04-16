"""
平台适配层。

按「宿主平台 × 通讯平台」维度组织适配逻辑，
解决"平台语义怎么读、怎么校验、怎么映射"。

目录结构（举例）::

    platforms/
      base.py               # CommProviderAdapter 抽象接口
      registry.py           # 注册表
      openclaw/
        comm/
          feishu.py          # OpenClaw + Feishu 适配器
      codex_cli/             # 未来
        comm/
          webhook.py
"""
