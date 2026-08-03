"""
数据库基础设施 - SQLite异步引擎、Session工厂、依赖注入、建表初始化
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
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
