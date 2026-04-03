"""
规则提示词路由 — CRUD + 合并获取
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt
from fastapi import Request

from app.database import get_db
from app.auth.dependencies import get_current_agent, verify_admin
from app.services import rule_service
from app.models.agent import Agent


router = APIRouter(prefix="/rules", tags=["Rule"])


# ============================================================
# 请求/响应模型
# ============================================================

class RuleCreateRequest(BaseModel):
    scope: str = Field(..., description="作用域: global/task/sub_task")
    content: str = Field(..., description="规则内容（Markdown）")
    task_id: Optional[str] = Field(None, description="任务 ID（task/sub_task 级别时必填）")
    sub_task_id: Optional[str] = Field(None, description="子任务 ID（sub_task 级别时必填）")


class RuleUpdateRequest(BaseModel):
    content: str = Field(..., description="更新后的规则内容")


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scope: str
    task_id: Optional[str]
    sub_task_id: Optional[str]
    content: str
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None


class MergedRulesResponse(BaseModel):
    content: str
    message: str = "合并后的规则（已替换变量）"
    # CLI 自更新字段
    update_available: bool = False
    latest_version: Optional[int] = None
    update_instructions: str = ""


# ============================================================
# Agent 获取合并规则（核心接口）
# ============================================================

@router.get("", response_model=MergedRulesResponse, summary="获取合并后的规则")
async def get_merged_rules(
    request: Request,
    task_id: Optional[str] = None,
    sub_task_id: Optional[str] = None,
    cli_version: Optional[int] = None,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取合并后的规则提示词（全局 + 任务 + 子任务），变量已替换

    cli_version: CLI 工具版本号（可选）
      - None: 旧版 CLI（不带版本号），在 content 末尾追加更新提示词
      - < latest: 版本过旧，通过 JSON 字段通知更新
      - >= latest: 版本最新，正常返回
    """
    from app.config import config

    content = rule_service.get_merged_rules(db, task_id=task_id, sub_task_id=sub_task_id)
    latest = config.cli_version

    # 解析服务地址（优先 external_url，Host 头兆底）
    base_url = config.server_external_url
    if not config.has_external_url:
        host = request.headers.get("host", "127.0.0.1:6565")
        scheme = "https" if request.url.scheme == "https" else "http"
        base_url = f"{scheme}://{host}"

    update_instructions = (
        f"\n执行以下命令一键更新（CLI + SKILL.md）：\n"
        f"  python task-cli.py --key <你的API_KEY> update\n\n"
        f"或手动下载：\n"
        f"  curl -o task-cli.py -H \"Authorization: Bearer <你的API_KEY>\" {base_url}/api/tools/cli\n"
        f"  curl -o SKILL.md -H \"Authorization: Bearer <你的API_KEY>\" {base_url}/api/agents/me/skill"
    )

    # 旧版 CLI（不带版本号）—— 在 content 末尾追加自然语言更新指引
    if cli_version is None:
        update_hint = (
            f"\n\n---\n\n"
            f"## ⚠️ 工具更新通知\n\n"
            f"你当前使用的 task-cli.py 版本过旧，请立即更新以获得最新功能：\n\n"
            f"1. 下载最新脚本：\n"
            f"   ```bash\n"
            f"   curl -o task-cli.py -H \"Authorization: Bearer <你的API_KEY>\" {base_url}/api/tools/cli\n"
            f"   ```\n"
            f"2. 下载最新技能提示词：\n"
            f"   ```bash\n"
            f"   curl -o SKILL.md -H \"Authorization: Bearer <你的API_KEY>\" {base_url}/api/agents/me/skill\n"
            f"   ```\n"
            f"3. 更新后的 task-cli.py 支持 `update` 命令，以后可以一键更新。"
        )
        return MergedRulesResponse(
            content=content + update_hint,
            update_available=True,
            latest_version=latest,
            update_instructions=update_instructions,
        )

    # 版本过旧
    if cli_version < latest:
        return MergedRulesResponse(
            content=content,
            update_available=True,
            latest_version=latest,
            update_instructions=update_instructions,
        )

    # 版本最新
    return MergedRulesResponse(content=content)


# ============================================================
# 管理端 CRUD
# ============================================================

@router.get("/list", response_model=List[RuleResponse], summary="查看规则列表")
async def list_rules(
    scope: Optional[str] = None,
    task_id: Optional[str] = None,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员查看规则列表"""
    return rule_service.list_rules(db, scope=scope, task_id=task_id)


@router.get("/{rule_id}", response_model=RuleResponse, summary="查看规则详情")
async def get_rule(
    rule_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员查看单条规则"""
    rule = rule_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    return rule


@router.post("", response_model=RuleResponse, summary="创建规则")
async def create_rule(
    req: RuleCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员创建规则"""
    try:
        rule = rule_service.create_rule(
            db, scope=req.scope, content=req.content,
            task_id=req.task_id, sub_task_id=req.sub_task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return rule


@router.put("/{rule_id}", response_model=RuleResponse, summary="更新规则")
async def update_rule(
    rule_id: str,
    req: RuleUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员更新规则内容"""
    try:
        rule = rule_service.update_rule(db, rule_id, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return rule


@router.delete("/{rule_id}", summary="删除规则")
async def delete_rule(
    rule_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员删除规则"""
    try:
        rule_service.delete_rule(db, rule_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "规则已删除"}
