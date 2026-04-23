"""提示词组合与对接引导渲染。"""

from app.config import config

from .agent import get_agent


ONBOARDING_MARKER = "## 🔧 平台对接"


def compose_prompt(slug: str) -> str:
    """
    生成完整 Prompt。
    Agent 文件内容已包含角色模板（创建时已合并），
    因此只需追加对接指引即可。
    """
    agent_data = get_agent(slug)
    if not agent_data:
        raise ValueError(f"Agent 提示词 '{slug}' 不存在")

    role = agent_data.get("role", "")
    agent_content = agent_data.get("content", "")

    if ONBOARDING_MARKER in agent_content:
        return agent_content.strip()

    parts = []
    if agent_content:
        parts.append(agent_content.strip())
    parts.append(generate_onboarding(role))

    return "\n\n---\n\n".join(parts)


def generate_onboarding(role: str = "") -> str:
    """生成平台对接指引文本（变量从 config 自动填充）。"""
    external_url = config.server_external_url
    registration_token = config.registration_token
    bs = "\\"

    lines = [
        "## 🔧 平台对接（仅用于首次注册，完成后请删除本段）",
        "",
        "> ⚠️ **重要提示**：以下内容仅用于首次注册，注册完成后务必从系统提示词中移除本段。",
        "> 请勿将本段写入 AGENTS.md、SOUL.md 或任何长期使用的系统提示词中。",
        "",
        "### 第一步：注册到任务系统（如已注册可跳过）",
        "",
        "```bash",
        f"curl -X POST {external_url}/api/agents/register {bs}",
        f'  -H "Content-Type: application/json" {bs}',
        f'  -H "X-Registration-Token: {registration_token}" {bs}',
        f"""  -d '{{"name": "你的名字", "role": "{role}", "description": "简要描述你的职责"}}'""",
        "```",
        "",
        "> **字段说明**：",
        "> - `name`：你的名字（如 AI小吴）",
        "> - `role`：角色类型（planner / executor / reviewer / patrol）",
        "> - `description`：简要描述你的职责（如「后端开发，负责 API 和数据库」）",
        "",
        "→ 返回你的 API Key，后续所有操作需要携带",
        "",
        "> ⚠️ **API Key 只在注册时显示一次，请务必立即记录。** 如果遗失，需要联系管理员重置。",
        "",
        "### 第二步：获取工作工具并保存为 Skill",
        "",
        "```bash",
        "# 下载 CLI 工具",
        f"curl -o task-cli.py {bs}",
        f'  -H "Authorization: Bearer 你的API_KEY" {bs}',
        f"  {external_url}/api/tools/cli",
        "",
        "# 获取技能提示词（Skill 说明，API Key 已自动填入）",
        f'curl -H "Authorization: Bearer 你的API_KEY" {bs}',
        f"  {external_url}/api/agents/me/skill",
        "```",
        "",
        "**请将以上内容保存为 Skill 目录**：",
        f"- 创建目录 `task-{role}-skill/`",
        f"- 将 CLI 工具保存为 `task-{role}-skill/task-cli.py`",
        f"- 将技能提示词保存为 `task-{role}-skill/SKILL.md`",
        "- Skill 是你的工作工具箱，后续按 SKILL.md 中的指引操作即可",
        "",
        "### 第三步：确认 API Key 已保存",
        "",
        "打开 SKILL.md，确认 `## 认证信息` 部分已包含你的 API Key：",
        "",
        "```markdown",
        "## 认证信息",
        "",
        "- API_KEY: `ock_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`",
        "```",
        "",
        "如果 API Key 未自动填入，请手动将注册时获得的 Key 填写到上述位置。",
        "",
        "### 第四步：开始工作",
        "",
        "```bash",
        "python task-cli.py rules    # 查看工作规则",
        "python task-cli.py next     # 领取任务",
        "python task-cli.py submit   # 提交成果",
        "```",
        "",
        "### 连接信息",
        f"- 服务地址: {external_url}",
        f"- 注册令牌: {registration_token}",
    ]
    return "\n".join(lines)
