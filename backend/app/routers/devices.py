"""
设备与系统 - 设备列表（类型筛选）、设备换绑、API用量监控
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Device, ApiUsage, Elder, LlmCallLog
from app.routers.auth import get_current_user, require_roles
from app.schemas import RebindRequest
from app.services.rbac import apply_village_filter

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
    query = apply_village_filter(query, Device, user)  # Phase 2: RBAC 行级隔离（预留，当前仅管理员可访问）

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


# ========== 添加设备（手动录入序列号）==========
class AddDeviceRequest(BaseModel):
    device_sn: str
    type: str               # BRACELET / GATEWAY / CAMERA
    mac: str
    village_name: str = ""
    village_id: int = None


@router.post("/devices")
async def add_device(
    req: AddDeviceRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """添加单台设备（摄像头序列号等），device_sn 即萤石设备序列号"""
    if req.type not in ("BRACELET", "GATEWAY", "CAMERA"):
        raise HTTPException(status_code=400, detail="设备类型无效")
    existing = (await db.execute(select(Device).where(Device.device_sn == req.device_sn))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="设备编号已存在")
    from datetime import datetime
    db.add(Device(
        device_sn=req.device_sn, type=req.type, mac=req.mac,
        village_name=req.village_name or None, village_id=req.village_id,
        is_online=1, create_time=datetime.now().isoformat(),
    ))
    await db.flush()
    return {"code": 200, "data": {"message": "添加成功", "device_sn": req.device_sn}}


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
    time_range: str = "day",
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """前端 ApiMonitor.vue: API 用量监控（真实数据，无假数据）

    time_range: day/week/month，影响 token_trend 天数范围（7/14/30 天）。
    数据来源：ApiUsage 表（聚合）+ Redis（实时计数）+ LlmCallLog（明细统计/趋势）。
    """
    from datetime import datetime, timedelta
    from app.services import ai_service

    result = await db.execute(select(ApiUsage))
    records = result.scalars().all()

    ezviz = {"calls_today": 0, "limit_daily": 5000, "status": "未接入"}
    llm = {
        "tokens_today": 0, "tokens_week": 0, "tokens_month": 0,
        "monthly_limit": 1000000, "api_calls_today": 0,
        "latency_ms": 0, "cost_estimate_cny": 0.0,
        "time_range": time_range,
        "success_rate": 0.0, "error_count": 0, "avg_latency_ms": 0,
        "qwen_configured": ai_service._is_qwen_configured(),
    }
    for r in records:
        if r.service_name == "ezviz":
            ezviz = {"calls_today": r.calls_today or 0, "limit_daily": r.limit_daily or 5000, "status": "未接入"}
        elif r.service_name == "qwen":
            llm.update({
                "tokens_today": r.tokens_today or 0, "tokens_week": r.tokens_week or 0,
                "tokens_month": r.tokens_month or 0, "monthly_limit": r.monthly_limit or 1000000,
                "api_calls_today": r.api_calls_today or 0,
                "latency_ms": r.latency_ms or 0,
                "cost_estimate_cny": r.cost_estimate or 0.0,
            })

    # Redis 实时计数覆盖数据库值
    try:
        from app.services.redis_client import get_api_counter
        qwen_redis = await get_api_counter("qwen")
        if qwen_redis:
            llm["api_calls_today"] = qwen_redis.get("api_calls", llm["api_calls_today"])
            llm["tokens_today"] = qwen_redis.get("tokens", llm["tokens_today"])
        ezviz_redis = await get_api_counter("ezviz")
        # Redis 可用：无计数也视为今日 0 次真实调用，不回退到过期的 DB 种子值（如 1234）
        ezviz["calls_today"] = ezviz_redis.get("calls", 0)
    except Exception:
        pass

    # 萤石配置状态：已配置真实凭证 → active，否则 未接入
    if settings.ezviz_app_key and settings.ezviz_app_key != "your-ezviz-app-key":
        ezviz["status"] = "active"

    # 今日 LlmCallLog 统计：成功率 / 错误数 / 平均延迟
    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = (await db.execute(
        select(func.count(LlmCallLog.id), func.avg(LlmCallLog.latency_ms))
        .where(LlmCallLog.created_date == today)
    )).one()
    today_total = today_stats[0] or 0
    llm["avg_latency_ms"] = int(today_stats[1] or llm["latency_ms"] or 0)
    today_success = (await db.execute(
        select(func.count(LlmCallLog.id)).where(
            LlmCallLog.created_date == today, LlmCallLog.status == "success",
        )
    )).scalar() or 0
    today_error = (await db.execute(
        select(func.count(LlmCallLog.id)).where(
            LlmCallLog.created_date == today,
            LlmCallLog.status.in_(("failed", "degraded", "skipped")),
        )
    )).scalar() or 0
    llm["error_count"] = today_error
    llm["success_rate"] = round(today_success / today_total * 100, 1) if today_total else 0.0

    # token_trend：按天聚合（day→7天 / week→14天 / month→30天）
    trend_days = {"day": 7, "week": 14, "month": 30}.get(time_range, 7)
    start_date = (datetime.now() - timedelta(days=trend_days - 1)).strftime("%Y-%m-%d")
    trend_rows = (await db.execute(
        select(
            LlmCallLog.created_date,
            func.sum(LlmCallLog.total_tokens),
            func.count(LlmCallLog.id),
            func.avg(LlmCallLog.latency_ms),
        ).where(LlmCallLog.created_date >= start_date)
        .group_by(LlmCallLog.created_date)
        .order_by(LlmCallLog.created_date)
    )).all()
    token_trend = [
        {"date": row[0], "tokens": row[1] or 0, "calls": row[2] or 0, "avg_latency_ms": int(row[3] or 0)}
        for row in trend_rows
    ]

    return {"code": 200, "data": {"ezviz_api": ezviz, "llm_qwen": llm, "token_trend": token_trend}}
