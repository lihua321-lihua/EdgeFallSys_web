"""
萤石 Webhook 回调 - 告警接入核心

流程：萤石布防触发 → Webhook回调 → HMAC-SHA1验签 → messageId幂等 → 告警落库 → WS推送 → 异步Qwen-VL分析

注意：/callback 无需认证（萤石平台调用，无法带JWT）；/callback/test 需管理员认证。
"""
import hmac
import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Alert
from app.config import settings
from app.routers.auth import require_roles

router = APIRouter(prefix="/api/v1/admin/ezviz", tags=["萤石Webhook"])


@router.post("/callback")
async def ezviz_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """萤石消息推送回调入口。必须 2 秒内返回 200 + {"messageId":"..."}。

    签名：HMAC-SHA1(secret, body + timestamp)，secret 为空时跳过验签（测试模式）。
    幂等：按 messageId 去重（Redis SETNX，TTL 24h）。
    """
    # 1. 提取签名头
    signature = request.headers.get("Signature", "")
    timestamp = request.headers.get("TimeStamp", "")

    # 2. 读取 body
    body = await request.body()
    body_text = body.decode("utf-8") if body else ""

    # 3. 验签（配置了签名密钥才验）
    if settings.ezviz_sign_secret:
        expected = hmac.new(
            settings.ezviz_sign_secret.encode(),
            (body_text + timestamp).encode(),
            hashlib.sha1,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=403, detail="签名验证失败")

    # 4. 解析消息
    try:
        msg = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="消息体格式错误")

    header = msg.get("header", {})
    message_id = header.get("messageId", "")
    msg_type = header.get("type", "")
    device_id = header.get("deviceId", "")

    # 5. 幂等检查（Redis SETNX，失败跳过=降级）
    if message_id:
        try:
            from app.services.redis_client import redis_client
            dedup_key = f"ezviz:msg:{message_id}"
            set_result = await redis_client.set(dedup_key, "1", ex=86400, nx=True)
            if not set_result:
                return {"messageId": message_id}  # 已处理过
        except Exception:
            pass

    # 6. 告警消息处理
    if msg_type == "ys.alarm":
        body_data = msg.get("body", {})
        alarm_type = body_data.get("alarmType", "motiondetect")
        pictures = body_data.get("pictureList", [])
        image_url = pictures[0].get("url", "") if pictures else ""

        event_id = f"EZV_{message_id[-12:]}" if message_id else f"EZV_{datetime.now().strftime('%H%M%S%f')}"
        alert_type = "INTRUSION_ALERT" if alarm_type in ("motiondetect", "pir") else "FALL_DETECTED"

        # 告警落库
        db.add(Alert(
            event_id=event_id,
            type=alert_type,
            level="HIGH",
            elder_name="摄像头告警",
            status="pending",
            create_time=int(datetime.now().timestamp()),
            location=device_id,
            title=f"萤石告警：{alarm_type}",
            ai_diagnosis="待AI分析" if image_url else "无截图",
        ))
        await db.flush()

        # WS 推送
        try:
            from app.services.ws_manager import ws_manager
            await ws_manager.broadcast_to_admins({
                "type": "alert",
                "event_id": event_id,
                "alert_type": alert_type,
                "level": "HIGH",
                "title": f"萤石告警：{alarm_type}",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat(),
            })
        except Exception:
            pass

        # 异步触发 Qwen-VL 图片分析
        if image_url:
            try:
                from app.celery_tasks import analyze_image_task
                analyze_image_task.delay(event_id, image_url, alert_type)
            except Exception as e:
                print(f"[Webhook] 图片分析任务派发失败: {e}")

    # 7. 2 秒内返回（萤石要求）
    return {"messageId": message_id}


@router.post("/callback/test", dependencies=[Depends(require_roles("admin", "super_admin"))])
async def test_callback(
    db: AsyncSession = Depends(get_db),
):
    """手动触发假告警（测试用，无需萤石平台配置）"""
    event_id = f"EZV_TEST_{datetime.now().strftime('%H%M%S')}"
    db.add(Alert(
        event_id=event_id, type="INTRUSION_ALERT", level="HIGH",
        elder_name="摄像头告警(测试)", status="pending",
        create_time=int(datetime.now().timestamp()),
        location="测试设备", title="萤石告警(测试)：移动侦测",
        ai_diagnosis="测试告警，无截图",
    ))
    await db.flush()

    try:
        from app.services.ws_manager import ws_manager
        await ws_manager.broadcast_to_admins({
            "type": "alert", "event_id": event_id,
            "title": "萤石告警(测试)：移动侦测",
            "timestamp": datetime.now().isoformat(),
        })
    except Exception:
        pass

    return {"code": 200, "data": {"message": "测试告警已创建", "event_id": event_id}}
