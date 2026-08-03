"""
规则引擎：自动分析数据，生成走访任务
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select
from app.models import Elder, DoorEvent, VisitTask, Device


async def check_door_inactive(db, days=3):
    """R1: 检测连续 N 天无门磁开门记录的老人（仅检测绑定了设备的老人）"""
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # 找到最近 N 天有开门记录的老人 ID 集合
    active_result = await db.execute(
        select(DoorEvent.elder_id).where(
            DoorEvent.event_type == "open",
            DoorEvent.event_date >= cutoff_date,  # ISO 日期字符串比较，跨年正确
        ).distinct()
    )
    active_ids = {row[0] for row in active_result}

    # 仅检查绑定了设备的老人（未绑定设备的老人无门磁数据，不应误报）
    elders = (await db.execute(
        select(Elder).where(Elder.device_sn.isnot(None))
    )).scalars().all()

    tasks = []
    for e in elders:
        if e.elder_id in active_ids:
            continue

        # 去重：检查是否已有相同类型的待处理任务
        exists = (await db.execute(
            select(VisitTask).where(
                VisitTask.elder_id == e.elder_id,
                VisitTask.status == "pending",
                VisitTask.trigger_reason.contains("门磁未触发"),
            )
        )).scalar_one_or_none()
        if exists:
            continue

        task = VisitTask(
            task_id=f"TASK-AUTO-{uuid4().hex[:8].upper()}",
            elder_name=e.name,
            elder_id=e.elder_id,
            village_id=e.village_id,
            trigger_reason=f"系统检测到老人连续{days}天门磁未触发（未出门），可能存在健康风险，建议上门查看。",
            status="pending",
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        db.add(task)
        tasks.append(task)

    return tasks


async def check_device_offline_24h(db):
    """R4: 设备离线超过 24 小时 → 生成走访任务（与 M6 的 2h 告警不同，此处生成走访任务）"""
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp())

    devices = (await db.execute(
        select(Device).where(
            Device.is_online == 0,
            Device.last_active < cutoff_ts,
            Device.bind_elder_id.isnot(None),  # 仅关注已绑定老人的设备
        )
    )).scalars().all()

    tasks = []
    for d in devices:
        # 去重（与生成文本中的"已离线超过24小时"标记匹配）
        exists = (await db.execute(
            select(VisitTask).where(
                VisitTask.elder_id == d.bind_elder_id,
                VisitTask.status == "pending",
                VisitTask.trigger_reason.contains("已离线超过24小时"),
            )
        )).scalar_one_or_none()
        if exists:
            continue

        task = VisitTask(
            task_id=f"TASK-AUTO-{uuid4().hex[:8].upper()}",
            elder_name=d.bind_elder or "未知",
            elder_id=d.bind_elder_id,
            village_id=d.village_id,
            trigger_reason=f"老人设备（{d.device_sn}）已离线超过24小时，建议上门确认。",
            status="pending",
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        db.add(task)
        tasks.append(task)

    return tasks


async def evaluate_all_rules(db):
    """执行所有规则，返回新生成的任务列表"""
    all_tasks = []
    all_tasks.extend(await check_door_inactive(db, days=3))
    all_tasks.extend(await check_device_offline_24h(db))
    all_tasks.extend(await check_uwb_single_room(db, days=3))
    all_tasks.extend(await check_heart_rate_anomaly(db, hours=24))
    return all_tasks


async def check_uwb_single_room(db, days=3):
    """R2: 检测连续 N 天 UWB 轨迹主要停留在单一房间的老人（可能卧床不起）
    判定逻辑：总活动房间数 ≤ 1，或主要房间停留占比 ≥ 95%
    """
    from app.services.tdengine_client import td_client

    elders = (await db.execute(
        select(Elder).where(Elder.device_sn.isnot(None))
    )).scalars().all()

    tasks = []
    for e in elders:
        try:
            stats = await td_client.query_uwb_room_stats(e.elder_id, days=days)
        except Exception:
            continue

        if not stats:
            continue

        total_stays = sum(row.get("stay_count", 0) for row in stats)
        if total_stays == 0:
            continue

        is_single_room = len(stats) == 1
        main_room_ratio = stats[0].get("stay_count", 0) / total_stays if total_stays > 0 else 0
        is_dominant_room = len(stats) > 1 and main_room_ratio >= 0.95

        if is_single_room or is_dominant_room:
            room_desc = f"仅停留{len(stats)}个房间" if is_single_room else f"主要房间停留占比{main_room_ratio:.0%}"
            exists = (await db.execute(
                select(VisitTask).where(
                    VisitTask.elder_id == e.elder_id,
                    VisitTask.status == "pending",
                    VisitTask.trigger_reason.contains("轨迹单一"),
                )
            )).scalar_one_or_none()
            if exists:
                continue

            task = VisitTask(
                task_id=f"TASK-AUTO-{uuid4().hex[:8].upper()}",
                elder_name=e.name,
                elder_id=e.elder_id,
                village_id=e.village_id,
                trigger_reason=f"系统检测到老人连续{days}天轨迹单一（{room_desc}），可能存在行动障碍，建议上门查看。",
                status="pending",
                create_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            db.add(task)
            tasks.append(task)

    return tasks


async def check_heart_rate_anomaly(db, hours=24):
    """R3: 检测手环心率异常（持续偏高 >120 或偏低 <50）
    判定逻辑：均值超过阈值 且 最近连续 3 条数据均在异常范围内
    """
    from app.services.tdengine_client import td_client

    elders = (await db.execute(
        select(Elder).where(Elder.device_sn.isnot(None))
    )).scalars().all()

    tasks = []
    for e in elders:
        try:
            data = await td_client.query_bracelet_recent(e.elder_id, hours=hours)
        except Exception:
            continue

        if not data:
            continue

        heart_rates = [row.get("heart_rate") for row in data if row.get("heart_rate")]
        if len(heart_rates) < 5:
            continue

        avg_hr = sum(heart_rates) / len(heart_rates)

        is_high = avg_hr > 120
        is_low = avg_hr < 50

        if not (is_high or is_low):
            continue

        recent_3 = heart_rates[:3]
        if is_high and not all(hr > 100 for hr in recent_3):
            continue
        if is_low and not all(hr < 55 for hr in recent_3):
            continue

        exists = (await db.execute(
            select(VisitTask).where(
                VisitTask.elder_id == e.elder_id,
                VisitTask.status == "pending",
                VisitTask.trigger_reason.contains("心率异常"),
            )
        )).scalar_one_or_none()
        if exists:
            continue

        direction = "偏高" if is_high else "偏低"
        task = VisitTask(
            task_id=f"TASK-AUTO-{uuid4().hex[:8].upper()}",
            elder_name=e.name,
            elder_id=e.elder_id,
            village_id=e.village_id,
            trigger_reason=f"系统检测到老人近{hours}小时心率持续{direction}（均值{avg_hr:.0f}），建议关注。",
            status="pending",
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        db.add(task)
        tasks.append(task)

    return tasks
