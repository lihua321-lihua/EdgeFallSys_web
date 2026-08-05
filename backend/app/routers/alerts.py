"""
告警工单 - 待处理告警列表（CRITICAL优先排序）、工单处理（角色差异化）
P0 修正：网格员现场处置 / 村医医疗判断，按角色分支 + AlertHandlingLog 流转留痕
"""
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, case
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as _BaseModel

from app.database import get_db
from app.models import Alert, Elder, AlertHandlingLog
from app.routers.auth import get_current_user, require_roles
from app.schemas import ResolveRequest
from app.services.ws_manager import ws_manager
from app.services.rbac import apply_village_filter, check_village_access, has_permission

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

# P0: 角色-操作映射表
# 网格员允许的现场处置操作 / 村医仅允许医疗判断操作
FIELD_ACTIONS = {"VISITED", "CALLED_FAMILY", "FALSE_ALARM"}
MEDICAL_ACTIONS = {"MEDICAL_JUDGE"}


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
            "action_type": a.action_type,        # 处理结果：VISITED/CALLED_FAMILY/FALSE_ALARM/MEDICAL_JUDGE
            "remark": a.remark,                  # 处理备注（网格员现场情况）
            "medical_judgment": a.medical_judgment,  # P0: 村医医疗判断
            "need_transfer": a.need_transfer,        # P0: 是否需要送医
            "handler_name": a.handler_name,      # 处理人
            "handle_time": a.handle_time,        # 处理完成时间（Unix 秒）
        })

    # 前端 AlertBoard.vue:128: alerts.value = res || []
    # 所以 data 直接是数组，不包 { items, total }
    return {"code": 200, "data": items}


async def _write_handling_log(db: AsyncSession, event_id: str, user, action: str, remark: str | None):
    """写入告警处理流转日志（AlertHandlingLog），实现跨角色协作留痕。"""
    log = AlertHandlingLog(
        event_id=event_id,
        handler_id=user.id,
        handler_role=user.role,
        action=action,
        remark=remark,
        handle_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(log)
    await db.flush()


@router.post("/{event_id}/resolve")
async def resolve_alert(
    event_id: str,
    req: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),  # 需要认证
):
    """处理工单 - P0 角色差异化

    网格员（village_grid）：仅允许 VISITED/CALLED_FAMILY/FALSE_ALARM（现场处置）
    村医（village_doctor）：仅允许 MEDICAL_JUDGE（医疗判断），需填 medical_judgment
    管理员/超管：不直接处理工单（C-04 管理不下沉原则），返回 403
    """
    result = await db.execute(select(Alert).where(Alert.event_id == event_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="工单不存在")
    check_village_access(alert.village_id, user)
    if alert.status == "resolved":
        raise HTTPException(status_code=400, detail="工单已处理，不可重复操作")

    # P0: 角色-action 合法性校验（基于权限矩阵）
    if user.role == "village_grid":
        if req.action_type not in FIELD_ACTIONS:
            raise HTTPException(
                status_code=403,
                detail=f"网格员仅可执行现场处置（VISITED/CALLED_FAMILY/FALSE_ALARM），当前操作 '{req.action_type}' 不被允许",
            )
        if not has_permission(user.role, "alert", "resolve_field"):
            raise HTTPException(status_code=403, detail="权限不足：网格员无现场处置权限")
    elif user.role == "village_doctor":
        if req.action_type not in MEDICAL_ACTIONS:
            raise HTTPException(
                status_code=403,
                detail=f"村医仅可执行医疗判断（MEDICAL_JUDGE），当前操作 '{req.action_type}' 不被允许",
            )
        if not has_permission(user.role, "alert", "resolve_medical"):
            raise HTTPException(status_code=403, detail="权限不足：村医无医疗判断权限")
        if not req.medical_judgment:
            raise HTTPException(status_code=400, detail="医疗判断不能为空")
    else:
        # admin / super_admin 不参与日常工单处理（C-04 管理不下沉）
        raise HTTPException(
            status_code=403,
            detail="管理员不直接处理工单，请通过工单全局视图转派",
        )

    # 写入告警主表
    alert.status = "resolved"
    alert.action_type = req.action_type
    alert.handler_name = user.display_name          # 处理人 = 当前登录账号
    alert.handle_time = int(time.time())             # 处理完成时间

    if user.role == "village_grid":
        alert.remark = req.remark                     # 网格员现场情况备注
    elif user.role == "village_doctor":
        alert.medical_judgment = req.medical_judgment  # 村医医疗判断
        alert.need_transfer = 1 if req.need_transfer else 0

    # P0: 写入流转日志（跨角色协作留痕）
    log_remark = req.medical_judgment if user.role == "village_doctor" else req.remark
    await _write_handling_log(db, event_id, user, req.action_type, log_remark)

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
    # 跌倒专用：置信度与结构化跌倒数据，用于触发救援简报生成
    confidence: float | None = None                    # 跌倒置信度 0~1，≥0.85 才调大模型
    fall_data: dict | None = None                      # 手环加速度/位置/生命体征等结构化数据


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

    # Step 9: 异步触发告警智能分类（Celery 写回 ai_diagnosis + 记 token）
    # Celery 未启动时 delay 抛异常，try/except 隔离，不影响告警入库与广播
    try:
        from app.celery_tasks import classify_alert_task
        elder_context = f"{elder.name}，{elder.age or '未知'}岁" if elder else ""
        classify_alert_task.delay(
            event_id=event_id,
            alert_type=req.type,
            alert_text=req.detail or req.title or "",
            elder_context=elder_context,
        )
    except Exception as e:
        print(f"[WARN] 告警分类任务派发失败（Celery 未启动？）: {e}")

    # 跌倒事件：置信度≥阈值时异步生成救援简报（9 模块 JSON + TXT 文件存档）
    # 断网/Key 未配置/置信度不足均在任务内走本地模板兜底，不阻断告警入库
    if req.type == "FALL_DETECTED":
        try:
            from app.celery_tasks import generate_rescue_briefing_task
            from app.config import settings as _settings
            confidence = req.confidence if req.confidence is not None else 1.0
            if confidence >= _settings.ai_report_fall_confidence_threshold:
                # 组装 fall_data：前端传入优先，否则用告警字段 + 档案补充
                fall_data = req.fall_data or {}
                if not fall_data.get("fall_location") and req.location:
                    fall_data["fall_location"] = req.location
                if not fall_data.get("fall_time"):
                    fall_data["fall_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if elder:
                    if not fall_data.get("medical_history") and elder.medical_history:
                        fall_data["medical_history"] = elder.medical_history
                    if not fall_data.get("emergency_contact") and elder.emergency_contact:
                        fall_data["emergency_contact"] = elder.emergency_contact
                    if not fall_data.get("emergency_relation") and elder.emergency_relation:
                        fall_data["emergency_relation"] = elder.emergency_relation
                generate_rescue_briefing_task.delay(
                    event_id=event_id, elder_id=req.elder_id,
                    fall_data=fall_data, confidence=confidence,
                )
        except Exception as e:
            print(f"[WARN] 救援简报任务派发失败（Celery 未启动？）: {e}")

    return {"code": 200, "data": {"event_id": event_id, "message": "告警已推送"}}
