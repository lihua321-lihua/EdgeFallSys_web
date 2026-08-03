"""
告警工单 - 待处理告警列表（CRITICAL优先排序）、工单处理（三选一+备注）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as _BaseModel

from app.database import get_db
from app.models import Alert, Elder
from app.routers.auth import get_current_user, require_roles
from app.schemas import ResolveRequest
from app.services.ws_manager import ws_manager
from app.services.rbac import apply_village_filter, check_village_access

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
    query = (
        select(Alert)
        .where(Alert.status == status)
    )
    query = apply_village_filter(query, Alert, user)  # Phase 2: RBAC 行级隔离
    result = await db.execute(
        query.order_by(LEVEL_ORDER, Alert.create_time.desc())  # CRITICAL 优先 + 时间倒序
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
    check_village_access(alert.village_id, user)
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="工单已处理，不可重复操作")

    alert.status = "resolved"
    alert.action_type = req.action_type
    alert.remark = req.remark
    await db.flush()

    return {"code": 200, "data": {"message": "工单已处理"}}


# —— 追加：告警摄入接口（Phase 2 供管理员手动测试，Phase 3 由 MQTT 客户端调用）——

class AlertIngestRequest(_BaseModel):
    """模拟网关/设备上报告警"""
    type: str                                          # FALL_DETECTED / SCAM_ALERT / INTRUSION_ALERT
    level: str                                         # CRITICAL / HIGH
    elder_id: str
    location: str = ""
    detail: str = ""
    title: str = ""


@router.post("/ingest")
async def ingest_alert(
    req: AlertIngestRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_roles("admin", "super_admin")),  # 仅管理员可调用
):
    """接收告警：写入数据库 + WebSocket 广播。
    Phase 2 供管理员手动测试，Phase 3 由 MQTT 客户端调用。"""
    import time

    # 查老人信息
    elder_result = await db.execute(select(Elder).where(Elder.elder_id == req.elder_id))
    elder = elder_result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")

    # 写入数据库
    event_id = f"EVT-{int(time.time())}"
    alert = Alert(
        event_id=event_id,
        type=req.type,
        level=req.level,
        elder_name=elder.name,
        elder_id=req.elder_id,
        village_id=elder.village_id,
        status="pending",
        create_time=int(time.time()),
        location=req.location,
        ai_diagnosis=req.detail,
        title=req.title,
    )
    db.add(alert)
    await db.flush()

    # WebSocket 广播
    ws_message = {
        "type": req.type,
        "event_id": event_id,
        "level": req.level,
        "elder_name": elder.name,
        "elder_id": req.elder_id,
        "timestamp": int(time.time() * 1000),
        "payload": {
            "title": req.title or "告警通知",
            "location": req.location,
            "ai_diagnosis": req.detail,
        },
    }
    if elder.village_id:
        await ws_manager.broadcast_to_village(elder.village_id, ws_message)
    if req.level == "CRITICAL":
        await ws_manager.broadcast_to_admins(ws_message)

    return {"code": 200, "data": {"event_id": event_id, "message": "告警已推送"}}
