"""
设备与系统 - 设备列表（类型筛选）、设备换绑、API用量监控
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Device, ApiUsage, Elder
from app.routers.auth import get_current_user, require_roles
from app.schemas import RebindRequest

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["设备 & 系统"],
    dependencies=[Depends(require_roles("admin", "super_admin"))],
)


# ========== 设备列表 ==========
@router.get("/devices")
async def list_devices(
    type: str = "",
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """前端 Dashboard.vue:119: devRes.value.items"""
    query = select(Device)
    if type in ("BRACELET", "GATEWAY", "CAMERA"):
        query = query.where(Device.type == type)

    result = await db.execute(query)
    devices = result.scalars().all()

    items = [
        {
            "device_sn": d.device_sn,
            "type": d.type,
            "mac": d.mac,
            "village_name": d.village_name,
            "bind_elder": d.bind_elder,
            "bind_elder_id": d.bind_elder_id,
            "is_online": bool(d.is_online),        # 前端 Dashboard.vue:123: d.is_online
            "battery_level": d.battery_level,       # 前端 Dashboard.vue:125: d.battery_level < 20
            "signal": d.signal,
            "last_active": d.last_active,
            "create_time": d.create_time,
        }
        for d in devices
    ]
    return {"code": 200, "data": {"items": items, "total": len(items)}}


# ========== 设备换绑 ==========
@router.post("/devices/rebind")
async def rebind_device(
    req: RebindRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    # 1. 更新设备表
    result = await db.execute(select(Device).where(Device.device_sn == req.device_sn))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 记录旧绑定，用于同步 elders 表
    old_elder_id = device.bind_elder_id

    device.bind_elder_id = req.elder_id

    # 2. 同步 elders 表：解绑旧老人 + 绑定新老人
    if old_elder_id:
        old_elder = (await db.execute(select(Elder).where(Elder.elder_id == old_elder_id))).scalar_one_or_none()
        if old_elder:
            old_elder.device_sn = None  # 旧老人解绑手环

    new_elder = (await db.execute(select(Elder).where(Elder.elder_id == req.elder_id))).scalar_one_or_none()
    if new_elder:
        new_elder.device_sn = device.device_sn  # 新老人绑定手环
        device.bind_elder = new_elder.name       # 同步更新设备表中的老人姓名

    await db.flush()

    return {"code": 200, "data": {"message": "换绑成功", "device_sn": device.device_sn, "elder_id": req.elder_id}}


# ========== API 用量 ==========
@router.get("/system/api-usage")
async def get_api_usage(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """前端 Dashboard.vue:129: apiUsage.value = apiRes.value"""
    result = await db.execute(select(ApiUsage))
    records = result.scalars().all()

    ezviz = {"calls_today": 0, "limit_daily": 5000}
    llm = {
        "tokens_today": 0, "tokens_week": 0, "tokens_month": 0,
        "monthly_limit": 1000000, "api_calls_today": 0,
        "latency_ms": 0, "cost_estimate_cny": 0.0,
    }
    for r in records:
        if r.service_name == "ezviz":
            ezviz = {"calls_today": r.calls_today or 0, "limit_daily": r.limit_daily or 5000}
        elif r.service_name == "qwen":
            llm = {
                "tokens_today": r.tokens_today or 0, "tokens_week": r.tokens_week or 0,
                "tokens_month": r.tokens_month or 0, "monthly_limit": r.monthly_limit or 1000000,
                "api_calls_today": r.api_calls_today or 0,
                "latency_ms": r.latency_ms or 0,
                "cost_estimate_cny": r.cost_estimate or 0.0,
            }

    return {"code": 200, "data": {"ezviz_api": ezviz, "llm_qwen": llm}}
