"""
告警工单 - 待处理告警列表（CRITICAL优先排序）、工单处理（三选一+备注）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Alert
from app.routers.auth import get_current_user, require_roles
from app.schemas import ResolveRequest

router = APIRouter(
    prefix="/api/v1/admin/alerts",
    tags=["告警工单"],
    dependencies=[Depends(require_roles("village_grid", "village_doctor", "admin", "super_admin"))],
)

# 告警级别排序权重：CRITICAL=0(最高) > HIGH=1 > MEDIUM=2 > LOW=3
LEVEL_ORDER = case(
    (Alert.level == "CRITICAL", 0),
    (Alert.level == "HIGH", 1),
    (Alert.level == "MEDIUM", 2),
    (Alert.level == "LOW", 3),
    else_=4,
)


@router.get("")
async def list_alerts(
    status: str = "pending",
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),  # 需要认证
):
    """获取告警列表。前端 AlertBoard.vue 期望 data 直接是数组"""
    result = await db.execute(
        select(Alert)
        .where(Alert.status == status)
        .order_by(LEVEL_ORDER, Alert.create_time.desc())  # CRITICAL 优先 + 时间倒序
    )
    alerts = result.scalars().all()

    items = []
    for a in alerts:
        items.append({
            "event_id": a.event_id,
            "type": a.type,
            "level": a.level,
            "elder_name": a.elder_name,
            "elder_id": a.elder_id,
            "status": a.status,
            "create_time": a.create_time,
            "payload": {
                "title": a.title,
                "location": a.location,
                "ai_diagnosis": a.ai_diagnosis,
            },
        })

    # 前端 AlertBoard.vue:128: alerts.value = res || []
    # 所以 data 直接是数组，不包 { items, total }
    return {"code": 200, "data": items}


@router.post("/{event_id}/resolve")
async def resolve_alert(
    event_id: str,
    req: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),  # 需要认证
):
    """处理工单"""
    result = await db.execute(select(Alert).where(Alert.event_id == event_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="工单不存在")
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="工单已处理，不可重复操作")

    alert.status = "resolved"
    alert.action_type = req.action_type
    alert.remark = req.remark
    await db.flush()

    return {"code": 200, "data": {"message": "工单已处理"}}
