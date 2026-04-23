"""
管理端路由 — 提示词管理（模板 + Agent 专属）
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.auth.dependencies import verify_admin
from app.services import prompt as prompt_service

router = APIRouter(prefix="/admin/prompts", tags=["Admin Prompts"])


# ── 请求模型 ─────────────────────────────────────────────

class AgentPromptCreateRequest(BaseModel):
    slug: str = Field(..., description="自定义名（不含角色前缀，如 article-writer）")
    name: str = Field(..., description="显示名称")
    role: str = Field(..., description="角色类型: planner/executor/reviewer/patrol")
    description: str = Field("", description="简介")
    content: str = Field(..., description="提示词正文")


class AgentPromptUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="显示名称")
    role: Optional[str] = Field(None, description="角色类型")
    description: Optional[str] = Field(None, description="简介")
    content: Optional[str] = Field(None, description="提示词正文")


class TemplateUpdateRequest(BaseModel):
    content: str = Field(..., description="模板内容")


# ── 模板接口 ─────────────────────────────────────────────

@router.get("/templates", summary="列出角色模板")
async def list_templates(_=Depends(verify_admin)):
    return prompt_service.list_templates()


@router.get("/templates/{role}", summary="获取角色模板")
async def get_template(role: str, _=Depends(verify_admin)):
    data = prompt_service.get_template(role)
    if not data:
        raise HTTPException(status_code=404, detail=f"角色模板 '{role}' 不存在")
    return data


@router.put("/templates/{role}", summary="更新角色模板")
async def update_template(role: str, req: TemplateUpdateRequest, _=Depends(verify_admin)):
    try:
        return prompt_service.update_template(role, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Agent 提示词接口 ─────────────────────────────────────

@router.get("/agents", summary="列出所有 Agent 提示词")
async def list_agents(_=Depends(verify_admin)):
    return prompt_service.list_agents()


@router.get("/agents/{slug}", summary="获取 Agent 提示词详情")
async def get_agent(slug: str, _=Depends(verify_admin)):
    data = prompt_service.get_agent(slug)
    if not data:
        raise HTTPException(status_code=404, detail=f"Agent 提示词 '{slug}' 不存在")
    return data


@router.post("/agents", summary="新建 Agent 提示词", status_code=201)
async def create_agent(req: AgentPromptCreateRequest, _=Depends(verify_admin)):
    try:
        return prompt_service.create_agent(
            slug=req.slug,
            name=req.name,
            role=req.role,
            description=req.description,
            content=req.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/agents/{slug}", summary="编辑 Agent 提示词")
async def update_agent(slug: str, req: AgentPromptUpdateRequest, _=Depends(verify_admin)):
    try:
        return prompt_service.update_agent(
            slug=slug,
            name=req.name,
            role=req.role,
            description=req.description,
            content=req.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/agents/{slug}", summary="删除 Agent 提示词")
async def delete_agent(slug: str, _=Depends(verify_admin)):
    try:
        prompt_service.delete_agent(slug)
        return {"message": f"已删除 '{slug}'"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Prompt 组合（一键复制） ──────────────────────────────

@router.get("/compose/{slug}", summary="生成完整 Prompt（一键复制用）")
async def compose_prompt(slug: str, _=Depends(verify_admin)):
    try:
        prompt = prompt_service.compose_prompt(slug)
        return {"slug": slug, "prompt": prompt}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/onboarding/{role}", summary="获取平台对接指引文本")
async def get_onboarding(role: str, _=Depends(verify_admin)):
    return {"role": role, "content": prompt_service.generate_onboarding(role)}
