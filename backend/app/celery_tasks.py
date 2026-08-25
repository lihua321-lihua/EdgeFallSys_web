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
                        elder.name, elder.age or 0, elder.gender or "未知", data_summary,
                        db=db, request_id=f"single:{elder_id}",
                    )
            finally:
                await engine.dispose()

        return asyncio.run(_do())
    except Exception as exc:
        self.retry(exc=exc)


# ============ Step 8 新增任务：用量归档 / 告警分类 / 萤石健康检查 ============

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def archive_api_usage_daily(self):
    """每日凌晨归档：重置 qwen today 字段，从 LlmCallLog 重算 week/month 滚动窗口。

    纠正平时累加产生的漂移；Redis 今日计数按日期 key 自然隔离，无需清理。
    """
    try:
        from datetime import datetime, timedelta

        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    from sqlalchemy import select, func
                    from app.models import ApiUsage, LlmCallLog

                    today = datetime.now().strftime("%Y-%m-%d")
                    week_start = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
                    month_start = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")

                    week_tokens = (await db.execute(
                        select(func.coalesce(func.sum(LlmCallLog.total_tokens), 0))
                        .where(LlmCallLog.created_date >= week_start)
                    )).scalar() or 0
                    month_tokens = (await db.execute(
                        select(func.coalesce(func.sum(LlmCallLog.total_tokens), 0))
                        .where(LlmCallLog.created_date >= month_start)
                    )).scalar() or 0

                    record = (await db.execute(
                        select(ApiUsage).where(ApiUsage.service_name == "qwen")
                    )).scalar_one_or_none()
                    if record is None:
                        record = ApiUsage(service_name="qwen", record_date=today)
                        db.add(record)
                    record.record_date = today
                    record.calls_today = 0
                    record.api_calls_today = 0
                    record.tokens_today = 0
                    record.cost_estimate = 0.0
                    record.tokens_week = week_tokens
                    record.tokens_month = month_tokens
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(_do())
        print("[Celery] API 用量日归档完成")
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def classify_alert_task(self, event_id: str, alert_type: str, alert_text: str = "", elder_context: str = ""):
    """异步告警分类：调大模型分析，写回 Alert.ai_diagnosis。

    事件触发（由 /ingest 调 delay），不进 beat 排期。
    Key 未配置时降级为规则分类，仍写回 ai_diagnosis。
    """
    try:
        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    from app.services.ai_service import classify_alert
                    result = await classify_alert(
                        db, alert_type=alert_type, alert_text=alert_text,
                        elder_context=elder_context, request_id=event_id,
                    )
                    from app.models import Alert
                    from sqlalchemy import select as _select
                    alert = (await db.execute(
                        _select(Alert).where(Alert.event_id == event_id)
                    )).scalar_one_or_none()
                    if alert:
                        category = result.get("category", "")
                        suggestion = result.get("suggestion", "")
                        alert.ai_diagnosis = f"【{category}】{suggestion}" if category else suggestion
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(_do())
        print(f"[Celery] 告警 {event_id} 分类完成")
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_rescue_briefing_task(self, event_id: str, elder_id: str, fall_data: dict, confidence: float = 0.0):
    """异步生成跌倒救援简报：调大模型生成 9 模块 JSON，落库 AiAnalysisReport + 写 JSON/TXT 文件。

    事件触发（由 /ingest 在 type=FALL_DETECTED 且 confidence≥阈值 时调 delay），不进 beat 排期。
    断网/Key 未配置/置信度不足/超限均走本地模板兜底，不报错。
    """
    try:
        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    from app.services.ai_service import generate_rescue_briefing
                    await generate_rescue_briefing(
                        db, elder_id=elder_id, fall_data=fall_data,
                        request_id=event_id, event_id=event_id,
                        confidence=confidence,
                    )
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(_do())
        print(f"[Celery] 跌倒事件 {event_id} 救援简报生成完成")
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def ezviz_health_check(self):
    """萤石凭证健康检查：已配置则调一次 get_device_list 产生真实计数 + 验证凭证。

    03:00 定时触发；凭证无效时打印告警，不影响系统运行。
    """
    try:
        async def _do():
            from app.services.ezviz_client import _is_configured, get_device_list
            if not _is_configured():
                print("[Celery] 萤石未配置，跳过健康检查")
                return
            res = await get_device_list(page_size=1)
            if res.get("code") == "200":
                print("[Celery] 萤石凭证有效，设备列表获取成功")
            else:
                print(f"[Celery] 萤石凭证异常或无设备: {res.get('msg', res)}")

        asyncio.run(_do())
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def analyze_image_task(self, event_id: str, image_url: str, alert_type: str = "FALL_DETECTED"):
    """异步图片分析：Qwen-VL 分析萤石告警截图，写回 Alert.ai_diagnosis。

    事件触发（由 Webhook /callback 调 delay），不进 beat 排期。
    """
    try:
        async def _do():
            engine, factory = _make_session()
            try:
                async with factory() as db:
                    from app.services.ai_service import analyze_alert_image
                    result = await analyze_alert_image(
                        db, image_url=image_url, alert_type=alert_type,
                        request_id=event_id,
                    )
                    from app.models import Alert
                    from sqlalchemy import select as _select
                    alert = (await db.execute(
                        _select(Alert).where(Alert.event_id == event_id)
                    )).scalar_one_or_none()
                    if alert:
                        labels = ", ".join(result.get("labels", []))
                        risk = result.get("risk_level", "")
                        reasoning = result.get("reasoning", "")
                        alert.ai_diagnosis = f"【{labels}】【{risk}】{reasoning}"
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(_do())
        print(f"[Celery] 图片分析完成 {event_id}")
    except Exception as exc:
        self.retry(exc=exc)
