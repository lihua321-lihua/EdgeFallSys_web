"""
数据库基础设施 - SQLite异步引擎、Session工厂、依赖注入、建表初始化
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# SQLite 不支持 pool_size / max_overflow / pool_pre_ping，按数据库类型条件传参
_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs = dict(echo=False)
if not _is_sqlite:
    _engine_kwargs.update(pool_size=20, max_overflow=10, pool_pre_ping=True)

engine = create_async_engine(settings.database_url, **_engine_kwargs)

# Session 工厂
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# SQLAlchemy 声明式基类（所有 ORM 模型继承它）
class Base(DeclarativeBase):
    pass


# FastAPI 依赖注入：每个请求获取一个独立的数据库会话，请求结束时自动提交或回滚
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 应用启动时自动创建所有表（等同于执行 CREATE TABLE IF NOT EXISTS）
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all 只创建缺失的表，不会给已存在的表补充新字段，
        # 因此对历史库需要显式做一次幂等的列补齐迁移。
        await _run_column_migrations(conn)


async def _existing_columns(conn, table_name: str) -> set:
    """获取某张表已存在的列名集合（兼容 SQLite / PostgreSQL）。"""
    if conn.dialect.name == "sqlite":
        result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        return {row[1] for row in result.fetchall()}
    result = await conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table_name},
    )
    return {row[0] for row in result.fetchall()}


async def _ensure_column(conn, table_name: str, column_name: str, column_ddl: str):
    """若列不存在则 ALTER TABLE ADD COLUMN（幂等）。"""
    if column_name not in await _existing_columns(conn, table_name):
        await conn.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_ddl}")
        )


async def _run_column_migrations(conn):
    """历史库补齐 Alert / VisitTask 的处理人、处理时间字段。"""
    await _ensure_column(conn, "alerts", "handler_name", "VARCHAR(50)")
    await _ensure_column(conn, "alerts", "handle_time", "INTEGER")
    await _ensure_column(conn, "visit_tasks", "handler_name", "VARCHAR(50)")
    await _ensure_column(conn, "visit_tasks", "handle_time", "VARCHAR(30)")
    # 账号强制改密标记（默认 0，存量账号不受影响）
    await _ensure_column(conn, "accounts", "must_change_password", "INTEGER NOT NULL DEFAULT 0")
