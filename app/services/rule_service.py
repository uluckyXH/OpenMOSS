"""
规则提示词业务逻辑 — 含三级合并与变量替换
"""
import uuid
from sqlalchemy.orm import Session

from app.models.rule import Rule
from app.config import config
from app.exceptions import ConflictError, NotFoundError, ValidationError


def create_rule(
    db: Session,
    scope: str,
    content: str,
    task_id: str = None,
    sub_task_id: str = None,
) -> Rule:
    """创建规则"""
    valid_scopes = {"global", "task", "sub_task"}
    if scope not in valid_scopes:
        raise ValidationError(f"无效作用域 '{scope}'，可选: {', '.join(valid_scopes)}")

    if scope == "task" and not task_id:
        raise ValidationError("task 级别规则必须指定 task_id")
    if scope == "sub_task" and not sub_task_id:
        raise ValidationError("sub_task 级别规则必须指定 sub_task_id")

    # 全局规则只允许一条
    if scope == "global":
        existing = db.query(Rule).filter(Rule.scope == "global").first()
        if existing:
            raise ConflictError("全局规则已存在，请编辑现有规则而非新建")

    rule = Rule(
        id=str(uuid.uuid4()),
        scope=scope,
        content=content,
        task_id=task_id,
        sub_task_id=sub_task_id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: str, content: str) -> Rule:
    """更新规则内容"""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise NotFoundError(f"规则 {rule_id} 不存在")

    rule.content = content
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: str) -> bool:
    """删除规则"""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise NotFoundError(f"规则 {rule_id} 不存在")

    db.delete(rule)
    db.commit()
    return True


def list_rules(db: Session, scope: str = None, task_id: str = None) -> list:
    """查询规则列表"""
    query = db.query(Rule)
    if scope:
        query = query.filter(Rule.scope == scope)
    if task_id:
        query = query.filter(Rule.task_id == task_id)
    return query.order_by(Rule.created_at).all()


def get_rule(db: Session, rule_id: str) -> Rule:
    """获取单条规则"""
    return db.query(Rule).filter(Rule.id == rule_id).first()


def _replace_variables(content: str) -> str:
    """替换规则中的变量"""
    variables = {
        "{{workspace_root}}": config.workspace_root,
        "{{project_name}}": config.project_name,
    }
    for var, value in variables.items():
        content = content.replace(var, value)
    return content


def get_merged_rules(
    db: Session,
    task_id: str = None,
    sub_task_id: str = None,
) -> str:
    """
    获取合并后的规则提示词（含变量替换）。
    合并顺序：全局规则 + 任务级规则 + 子任务级规则
    """
    parts = []

    # 1. 全局规则
    global_rules = db.query(Rule).filter(Rule.scope == "global").order_by(Rule.created_at).all()
    for r in global_rules:
        parts.append(r.content)

    # 2. 任务级规则
    if task_id:
        task_rules = db.query(Rule).filter(
            Rule.scope == "task",
            Rule.task_id == task_id,
        ).order_by(Rule.created_at).all()
        for r in task_rules:
            parts.append(r.content)

    # 3. 子任务级规则
    if sub_task_id:
        sub_task_rules = db.query(Rule).filter(
            Rule.scope == "sub_task",
            Rule.sub_task_id == sub_task_id,
        ).order_by(Rule.created_at).all()
        for r in sub_task_rules:
            parts.append(r.content)

    # 合并 + 变量替换
    merged = "\n\n---\n\n".join(parts) if parts else ""
    return _replace_variables(merged)
