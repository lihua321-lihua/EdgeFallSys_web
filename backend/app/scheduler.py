"""
APScheduler 定时任务调度（AsyncIOScheduler）
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import async_session

scheduler = AsyncIOScheduler()


async def job_generate_reports():
    from app.services.llm_helper import generate_all_reports
    await generate_all_reports(async_session)


async def job_rule_engine():
    from app.services.rule_engine import evaluate_all_rules
    async with async_session() as db:
        tasks = await evaluate_all_rules(db)
        if tasks:
            await db.commit()
            print(f"[Scheduler] 规则引擎生成 {len(tasks)} 条走访任务")


async def job_device_monitor():
    from app.services.device_monitor import check_offline_devices, check_low_battery
    async with async_session() as db:
        await check_offline_devices(db)
        await check_low_battery(db)
        await db.commit()
        print("[Scheduler] 设备监控检查完成")


def start_scheduler():
    scheduler.add_job(job_generate_reports, 'cron', hour=2, minute=0, id='ai_report', replace_existing=True)
    scheduler.add_job(job_rule_engine, 'cron', hour=6, minute=0, id='rule_engine', replace_existing=True)
    scheduler.add_job(job_device_monitor, 'interval', minutes=30, id='device_monitor', replace_existing=True)
    scheduler.start()
    print("[Scheduler] 定时任务已启动")
    return scheduler
