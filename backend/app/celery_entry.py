"""
Celery Worker / Beat 启动入口
用法：
  celery -A app.celery_entry worker --loglevel=info --pool=solo
  celery -A app.celery_entry beat --loglevel=info
  celery -A app.celery_entry flower --port=5555
"""
from app.celery_app import celery_app
import app.celery_tasks  # noqa: F401 — 显式导入确保任务注册

__all__ = ["celery_app"]
