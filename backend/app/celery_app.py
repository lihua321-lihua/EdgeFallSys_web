"""
Celery 应用配置
Broker: Redis | Backend: Redis | Beat: 定时调度
"""
import os
from celery import Celery
from celery.schedules import crontab

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

celery_app = Celery(
    "edgefall",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    timezone="Asia/Shanghai",
    enable_utc=True,

    result_expires=3600,

    worker_concurrency=4,
    worker_prefetch_multiplier=2,

    task_acks_late=True,
    task_reject_on_worker_lost=True,

    beat_schedule={
        "generate-reports": {
            "task": "app.celery_tasks.generate_health_reports",
            "schedule": crontab(hour=2, minute=0),
        },
        "rule-engine": {
            "task": "app.celery_tasks.run_rule_engine",
            "schedule": crontab(hour=6, minute=0),
        },
        "device-monitor": {
            "task": "app.celery_tasks.run_device_monitor",
            "schedule": crontab(minute="*/30"),
        },
        # Step 8: 用量归档（每日 00:05 重置 today + 重算 week/month 滚动窗口）
        "archive-api-usage": {
            "task": "app.celery_tasks.archive_api_usage_daily",
            "schedule": crontab(hour=0, minute=5),
        },
        # Step 8: 萤石凭证健康检查（每日 03:00，产生真实调用计数）
        "ezviz-health-check": {
            "task": "app.celery_tasks.ezviz_health_check",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["app"])
