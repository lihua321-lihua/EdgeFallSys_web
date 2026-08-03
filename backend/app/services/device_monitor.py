"""
设备监控：离线/低电量检测 + WebSocket 告警推送
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models import Device, Alert
from app.services.ws_manager import ws_manager
from app.services.redis_client import cache_device_status
import time


async def check_offline_devices(db):
    """设备离线超过 2 小时 → 生成告警（M6 设备级告警，与 R4 走访任务不同）"""
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp())

    devices = (await db.execute(
        select(Device).where(
            Device.is_online == 0,
            Device.last_active < cutoff_ts,
        )
    )).scalars().all()

    for d in devices:
        # 去重
        exists = (await db.execute(
            select(Alert).where(
                Alert.event_id.like(f"DEV-OFF-{d.device_sn}%"),
                Alert.status == "pending",
            )
        )).scalar_one_or_none()
        if exists:
            continue

        alert = Alert(
            event_id=f"DEV-OFF-{d.device_sn}-{int(time.time())}",
            type="DEVICE_OFFLINE",
            level="HIGH",
            elder_name=d.bind_elder or "未绑定",
            elder_id=d.bind_elder_id,
            village_id=d.village_id,
            title=f"设备离线告警：{d.device_sn}",
            location=d.village_name or "",
            create_time=int(time.time()),
        )
        db.add(alert)
        await db.flush()

        # WebSocket 广播到管理员
        await ws_manager.broadcast_to_admins({
            "type": "device_offline",
            "level": "HIGH",
            "device_sn": d.device_sn,
            "village_name": d.village_name,
            "elder_name": d.bind_elder,
            "timestamp": int(time.time() * 1000),
        })

        # 缓存设备离线状态
        await cache_device_status(d.device_sn, {
            "is_online": False,
            "last_active": d.last_active,
            "battery_level": d.battery_level,
            "bind_elder": d.bind_elder,
        })


async def check_low_battery(db):
    """设备电量低于 10% → 生成告警"""
    devices = (await db.execute(
        select(Device).where(
            Device.type == "BRACELET",
            Device.battery_level < 10,
            Device.battery_level.isnot(None),
        )
    )).scalars().all()

    for d in devices:
        exists = (await db.execute(
            select(Alert).where(
                Alert.event_id.like(f"DEV-BAT-{d.device_sn}%"),
                Alert.status == "pending",
            )
        )).scalar_one_or_none()
        if exists:
            continue

        alert = Alert(
            event_id=f"DEV-BAT-{d.device_sn}-{int(time.time())}",
            type="DEVICE_LOW_BATTERY",
            level="HIGH",
            elder_name=d.bind_elder or "未绑定",
            elder_id=d.bind_elder_id,
            village_id=d.village_id,
            title=f"低电量告警：{d.device_sn}（{d.battery_level}%）",
            location=d.village_name or "",
            create_time=int(time.time()),
        )
        db.add(alert)
        await db.flush()

        await ws_manager.broadcast_to_admins({
            "type": "device_low_battery",
            "level": "HIGH",
            "device_sn": d.device_sn,
            "battery": d.battery_level,
            "elder_name": d.bind_elder,
            "timestamp": int(time.time() * 1000),
        })
