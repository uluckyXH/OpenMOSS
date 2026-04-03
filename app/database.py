"""
OpenMOSS 任务调度中间件 — 数据库初始化
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import config

Base = declarative_base()


def build_database_url() -> str:
    """构建正式环境使用的数据库 URL。"""
    return config.database_url


def build_engine_options(database_url: str) -> dict:
    """按数据库类型返回 SQLAlchemy engine 参数。"""
    options = {"echo": False}
    if make_url(database_url).get_backend_name() == "sqlite":
        # SQLite 在当前线程模型下需要显式关闭线程检查
        options["connect_args"] = {"check_same_thread": False}
    return options


def ensure_database_ready(database_url: str) -> None:
    """确保数据库运行前置条件满足。"""
    url = make_url(database_url)

    if url.get_backend_name() != "sqlite":
        return

    if not url.database or url.database == ":memory:":
        return

    Path(url.database).parent.mkdir(parents=True, exist_ok=True)


DATABASE_URL = build_database_url()
ENGINE_OPTIONS = build_engine_options(DATABASE_URL)
ensure_database_ready(DATABASE_URL)

engine = create_engine(DATABASE_URL, **ENGINE_OPTIONS)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
        managed_agent,
    )

    Base.metadata.create_all(bind=engine)
    print(f"[Database] 数据库初始化完成，共 {len(Base.metadata.tables)} 张表")

    # 静默迁移旧状态值（available/busy → active，offline → disabled）
    _migrate_agent_statuses()

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
