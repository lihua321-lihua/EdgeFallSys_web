"""
Celery 任务定义
将 APScheduler 任务迁移到 Celery，支持异步执行和重试

注意：每个任务使用独立的 asyncio.run() + 独立的数据库引擎/会话，
避免跨事件循环的连接池冲突
"""
import asyncio

from app.celery_app import celery_app
from app.config import settings


def _make_session():
    """为每次任务执行创建独立的引擎和会话工厂"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_health_reports(self):
    try:
        from app.services.llm_helper import generate_all_reports

        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    await generate_all_reports(db)
            finally:
                await engine.dispose()

        asyncio.run(_do())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_rule_engine(self):
    try:
        from app.services.rule_engine import evaluate_all_rules

        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    tasks = await evaluate_all_rules(db)
                    if tasks:
                        await db.commit()
                    return len(tasks) if tasks else 0
            finally:
                await engine.dispose()

        count = asyncio.run(_do())
        print(f"[Celery] 规则引擎生成 {count} 条走访任务")
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def run_device_monitor(self):
    try:
        from app.services.device_monitor import check_offline_devices, check_low_battery

        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    await check_offline_devices(db)
                    await check_low_battery(db)
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(_do())
        print("[Celery] 设备监控检查完成")
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def generate_single_report(self, elder_id: str):
    try:
        from app.services.llm_helper import generate_health_report
        from app.models import Elder
        from sqlalchemy import select

        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
                    elder = result.scalar_one_or_none()
                    if not elder:
                        return None
                    data_summary = f"年龄{elder.age}岁，住址{elder.address}。"
                    if elder.medical_history:
                        data_summary += f"既往病史：{elder.medical_history}。"
                    return await generate_health_report(
                        elder.name, elder.age or 0, elder.gender or "未知", data_summary
                    )
            finally:
                await engine.dispose()

        return asyncio.run(_do())
    except Exception as exc:
        self.retry(exc=exc)
