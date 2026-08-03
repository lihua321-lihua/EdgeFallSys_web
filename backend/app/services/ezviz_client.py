"""
萤石开放平台 API 封装
Phase 2: 仅做 API 调用计数，实际视频/人形检测集成在 Phase 3
"""
import os
from datetime import datetime, timezone
from sqlalchemy import select
from app.models import ApiUsage

EZVIZ_APP_KEY = os.getenv("EZVIZ_APP_KEY", "")
EZVIZ_APP_SECRET = os.getenv("EZVIZ_APP_SECRET", "")


async def record_ezviz_call(db, count=1):
    """记录萤石 API 调用次数（跨天自动重置 calls_today）"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result = await db.execute(
        select(ApiUsage).where(ApiUsage.service_name == "ezviz")
    )
    record = result.scalar_one_or_none()
    if record:
        if record.record_date != today:
            record.calls_today = count
            record.record_date = today
        else:
            record.calls_today = (record.calls_today or 0) + count
        await db.flush()


async def get_device_list(db):
    """获取萤石设备列表（Phase 2 仅计数，不返回真实数据）"""
    await record_ezviz_call(db)
    return {"message": "萤石 API 对接在 Phase 3 完成"}
