"""
OpenMOSS 任务调度中间件 — 数据库初始化
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import config

# 确保数据目录存在
import os
db_dir = os.path.dirname(config.database_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# SQLAlchemy 引擎
DATABASE_URL = f"sqlite:///{config.database_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库：导入所有模型并创建表"""
    # 导入所有模型，确保 Base.metadata 知道所有表
    from app.models import (  # noqa: F401
        agent,
        task,
        module,
        sub_task,
        rule,
        activity_log,
        review_record,
        reward_log,
        patrol_record,
        team,
    )

    Base.metadata.create_all(bind=engine)
    print(f"[Database] 数据库初始化完成，共 {len(Base.metadata.tables)} 张表")

    # 静默迁移旧状态值（available/busy → active，offline → disabled）
    _migrate_agent_statuses()

    # 迁移团队相关字段
    _migrate_team_fields()

    # 首次启动时，自动导入全局规则模板
    _load_default_rules()


def _migrate_agent_statuses():
    """静默迁移旧 Agent 状态值，仅影响 available/busy/offline"""
    from sqlalchemy import text

    db = SessionLocal()
    try:
        r1 = db.execute(
            text("UPDATE agent SET status = 'active' WHERE status IN ('available', 'busy')")
        )
        r2 = db.execute(
            text("UPDATE agent SET status = 'disabled' WHERE status = 'offline'")
        )
        total = r1.rowcount + r2.rowcount
        if total:
            db.commit()
            print(f"[Database] 已静默迁移 {total} 个 Agent 状态（旧值 → active/disabled）")
        else:
            db.rollback()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _load_default_rules():
    """首次启动时导入 rules/global-rule-example.md 作为全局规则"""
    from app.models.rule import Rule
    import uuid

    db = SessionLocal()
    try:
        # 已有全局规则，跳过
        existing = db.query(Rule).filter(Rule.scope == "global").first()
        if existing:
            return

        rule_file = os.path.join(os.getcwd(), "rules", "global-rule-example.md")
        if not os.path.exists(rule_file):
            return

        with open(rule_file, "r", encoding="utf-8") as f:
            content = f.read()

        rule = Rule(
            id=str(uuid.uuid4()),
            scope="global",
            content=content,
        )
        db.add(rule)
        db.commit()
        print(f"[Database] 已导入全局规则模板 → rules/global-rule-example.md")
    finally:
        db.close()


def _migrate_team_fields():
    """迁移团队相关字段：task.team_id, sub_task.remarks"""
    from sqlalchemy import text, inspect

    db = SessionLocal()
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # 为 task 表添加 team_id 字段
        if "task" in tables:
            task_columns = [c["name"] for c in inspector.get_columns("task")]
            if "team_id" not in task_columns:
                db.execute(text("ALTER TABLE task ADD COLUMN team_id VARCHAR(36) REFERENCES team(id)"))
                db.commit()
                print("[Database] 已迁移 task 表添加 team_id 字段")

        # 为 sub_task 表添加 remarks 字段
        if "sub_task" in tables:
            subtask_columns = [c["name"] for c in inspector.get_columns("sub_task")]
            if "remarks" not in subtask_columns:
                db.execute(text("ALTER TABLE sub_task ADD COLUMN remarks TEXT"))
                db.commit()
                print("[Database] 已迁移 sub_task 表添加 remarks 字段")
    except Exception as e:
        db.rollback()
        print(f"[Database] 迁移字段失败: {e}")
    finally:
        db.close()
