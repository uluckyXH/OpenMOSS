# MOSS Agent 集群安全加固方案
# 生成时间: 2026-03-16
# 作者: 小墨 (安全审查)

---

## 🔴 立即执行的安全修复

### 1. 脚本安全加固 ✅ 已修复
- [x] transcribe.sh 添加安全模式 (set -euo pipefail)
- [x] 添加文件类型检查 (.ogg 后缀验证)
- [x] 添加 trap EXIT 清理机制

### 2. OpenMOSS 后端安全配置

```yaml
# config.yaml 建议修改
server:
  host: 127.0.0.1  # 从 0.0.0.0 改为本地绑定
  port: 6565

agent:
  allow_registration: true
  registration_token: ${OPENMOSS_TOKEN}  # 使用环境变量
  
security:
  # 添加沙箱配置
  sandbox:
    enabled: true
    default_mode: "readonly"  # 默认只读
    allowed_paths:
      - ./workspace
      - ./shared_knowledge
    forbidden_paths:
      - /etc
      - ~/.ssh
      - ~/.openclaw/credentials
  
  # 网络限制
  network:
    whitelist:
      - api.openai.com
      - kimi.com
      - feishu.cn
    blacklist:
      - localhost:*
      - 127.0.0.1:*
      - 192.168.*
      - 10.*
```

### 3. Agent 权限分级

```yaml
# agent-permissions.yaml
agents:
  crawler-master:
    level: "restricted"
    filesystem: "readonly"
    network: "whitelist-only"
    allowed_hosts:
      - "*.gov.cn"
      - "xinhuanet.com"
      - "people.com.cn"
      
  writer:
    level: "standard"
    filesystem: "workspace-write"
    network: "none"  # 写作Agent不需要网络
    
  reviewer:
    level: "readonly"
    filesystem: "readonly"
    network: "none"
    
  planner:
    level: "standard"
    filesystem: "workspace-write"
    network: "whitelist-only"
```

### 4. 执行审批强化

```json
// exec-approvals.json 建议配置
{
  "commands": {
    "blacklist": [
      "rm -rf /",
      "sudo",
      "curl.*\|.*sh",
      "wget.*\|.*sh",
      ">.*\/etc\/",
      "dd if=",
      "mkfs",
      "format"
    ],
    "whitelist": [
      "ls",
      "cat",
      "grep",
      "find",
      "ffmpeg",
      "git"
    ]
  },
  "auto_approve": false,
  "timeout_seconds": 300
}
```

---

## 🟡 中期安全升级

### 1. 数据加密
- [ ] 数据库加密 (tasks.db)
- [ ] 敏感配置加密存储
- [ ] 通信加密 (HTTPS/TLS)

### 2. 审计日志
- [ ] 所有 Agent 操作记录
- [ ] 文件访问日志
- [ ] 网络请求日志
- [ ] 异常行为检测

### 3. 备份机制
- [ ] 数据库自动备份 (每日)
- [ ] 配置文件版本控制
- [ ] 灾难恢复预案

### 4. 监控告警
- [ ] CPU/内存使用监控
- [ ] 异常进程检测
- [ ] 网络流量监控
- [ ] 文件变更监控

---

## 🟢 长期安全规划

### 1. 代码安全审查
- [ ] 所有技能文件安全扫描
- [ ] 依赖包漏洞扫描
- [ ] 定期安全审计

### 2. 安全测试
- [ ] 渗透测试
- [ ] 模糊测试
- [ ] 沙箱逃逸测试

### 3. 合规性
- [ ] 数据隐私保护
- [ ] 访问控制审计
- [ ] 安全事件响应流程

---

## 🚨 安全红线

**绝对禁止**:
1. ❌ 在代码中硬编码密码/令牌
2. ❌ Agent 访问用户 home 目录的敏感文件
3. ❌ 无限制的网络访问
4. ❌ 无审批的高危命令执行
5. ❌ 敏感信息输出到日志

**必须遵守**:
1. ✅ 所有脚本使用 `set -euo pipefail`
2. ✅ 用户输入必须验证和转义
3. ✅ 临时文件必须清理
4. ✅ 错误信息不能泄露系统信息
5. ✅ 定期更换访问令牌

---

## 📋 安全检查清单

### 每次升级前检查:
- [ ] 新代码是否通过安全扫描?
- [ ] 是否有新的高危命令?
- [ ] 权限配置是否正确?
- [ ] 敏感信息是否已移除?

### 每周检查:
- [ ] 系统日志异常分析
- [ ] 备份是否正常
- [ ] 安全更新是否已应用

### 每月检查:
- [ ] 安全策略审查
- [ ] 权限审计
- [ ] 漏洞扫描

---

**制定时间**: 2026-03-16  
**安全级别**: 🔴 高危 - 需要立即处理  
**负责人**: 小墨 🦋
