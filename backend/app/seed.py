"""
种子数据脚本 - 从前端Mock JSON读取数据，批量写入SQLite数据库
Phase 2: 新增乡镇/村庄、门磁事件、AI 报告种子数据
"""
import json
import asyncio
from pathlib import Path
from passlib.context import CryptContext
from sqlalchemy import select

from app.database import async_session, init_db
from app.models import (
    Account, Elder, Device, Alert, VisitTask, ApiUsage,
    HealthReport, DoorEvent, Town, Village,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "123456"

# 前端 Mock 数据目录（相对于 backend/ 目录）
MOCK_DIR = Path(__file__).parent.parent.parent / "edgefall-web" / "src" / "mock"


def load_json(filename):
    """从 Mock 目录加载 JSON 文件"""
    path = MOCK_DIR / filename
    if not path.exists():
        print(f"  [WARN] {filename} 不存在，跳过")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def run():
    print("初始化数据库表...")
    await init_db()
    print("完成\n")

    async with async_session() as db:
        # —— 1. 账号 ——
        print("导入种子数据:")
        accounts = [
            ("zhang_grid", "张网格员", "village_grid", 1),
            ("li_doctor", "李村医", "village_doctor", 1),
            ("wang_admin", "王管理员", "admin", None),
            ("root", "超级管理员", "super_admin", None),
        ]
        for uname, dname, role, vid in accounts:
            db.add(Account(
                username=uname,
                password_hash=pwd_context.hash(DEFAULT_PASSWORD),
                display_name=dname,
                role=role,
                village_id=vid,
                status="active",
            ))
        print(f"  [OK] {len(accounts)} 个账号 (默认密码: {DEFAULT_PASSWORD})")

        # —— 2. 老人 ——
        elders_data = load_json("elders.json")
        detail = load_json("elder-detail.json") or {}
        if elders_data:
            for e in elders_data:
                extra = detail if e.get("elder_id") == detail.get("elder_id") else {}
                db.add(Elder(
                    elder_id=e["elder_id"], name=e["name"], age=e.get("age"),
                    gender=e.get("gender"), address=e.get("address"),
                    device_sn=e.get("device_sn"), gateway_sn=e.get("gateway_sn"),
                    emergency_contact=e.get("emergency_contact"),
                    emergency_relation=extra.get("emergency_relation"),
                    medical_history=extra.get("medical_history"),
                    bind_duration=extra.get("bind_duration"),
                    risk_tags=json.dumps(e.get("risk_tags", []), ensure_ascii=False),
                ))
            print(f"  [OK] {len(elders_data)} 位老人")

        # —— 3. 设备 ——
        devices_data = load_json("devices.json")
        if devices_data:
            for d in devices_data:
                db.add(Device(
                    device_sn=d["device_sn"], type=d["type"], mac=d["mac"],
                    village_name=d.get("village_name"),
                    bind_elder=d.get("bind_elder"), bind_elder_id=d.get("bind_elder_id"),
                    is_online=1 if d.get("is_online") else 0,
                    battery_level=d.get("battery_level"), signal=str(d.get("signal", "")),
                    last_active=d.get("last_active"), create_time=d.get("create_time"),
                ))
            print(f"  [OK] {len(devices_data)} 台设备")

        # —— 4. 告警 ——
        alerts_data = load_json("alerts.json")
        if alerts_data:
            for a in alerts_data:
                p = a.get("payload", {})
                db.add(Alert(
                    event_id=a["event_id"], type=a["type"], level=a["level"],
                    elder_name=a["elder_name"], elder_id=a.get("elder_id"),
                    status=a.get("status", "pending"), create_time=a.get("create_time"),
                    location=p.get("location"), ai_diagnosis=p.get("ai_diagnosis"),
                    title=p.get("title"),
                ))
            print(f"  [OK] {len(alerts_data)} 条告警")

        # —— 5. 走访任务 ——
        tasks_data = load_json("tasks.json")
        if tasks_data:
            for t in tasks_data:
                db.add(VisitTask(
                    task_id=t["task_id"], elder_name=t["elder_name"],
                    elder_id=t.get("elder_id"), trigger_reason=t.get("trigger_reason"),
                    status=t.get("status", "pending"), create_time=t.get("create_time"),
                    feedback=t.get("feedback"),
                ))
            print(f"  [OK] {len(tasks_data)} 条走访任务")

        # —— 6. API 用量 ——
        api_data = load_json("api-usage.json")
        if api_data:
            ezviz = api_data.get("ezviz_api", {})
            db.add(ApiUsage(service_name="ezviz", calls_today=ezviz.get("calls_today", 0),
                            limit_daily=ezviz.get("limit_daily", 5000), record_date="2026-06-16"))
            llm = api_data.get("llm_qwen", {})
            db.add(ApiUsage(service_name="qwen", tokens_today=llm.get("tokens_today", 0),
                            tokens_week=llm.get("tokens_week", 0), tokens_month=llm.get("tokens_month", 0),
                            api_calls_today=llm.get("api_calls_today", 0),
                            monthly_limit=llm.get("monthly_limit", 1000000),
                            latency_ms=llm.get("latency_ms", 0),
                            cost_estimate=llm.get("cost_estimate_cny", 0), record_date="2026-06-16"))
            print("  [OK] API 用量数据")

        # —— Phase 2 新增种子数据 ——
        print("导入 Phase 2 种子数据:")

        # 乡镇 + 村庄
        db.add(Town(id=1, name="桂花镇"))
        db.add(Village(id=1, town_id=1, name="桂花村"))
        db.add(Village(id=2, town_id=1, name="杨柳村"))
        db.add(Village(id=3, town_id=1, name="石门村"))
        db.add(Village(id=4, town_id=1, name="桃花村"))
        print("  [OK] 1 个乡镇 + 4 个村庄")

        # 回填已有表的 village_id（所有种子数据都属于桂花村，village_id=1）
        for table in [Elder, Device, Alert, VisitTask]:
            result = await db.execute(select(table))
            for row in result.scalars().all():
                row.village_id = 1
        print("  [OK] 回填 Elder/Device/Alert/VisitTask 的 village_id=1")

        # 门磁事件种子数据（从 elder-detail.json 的 recent_activities 提取）
        detail = load_json("elder-detail.json") or {}
        activities = detail.get("recent_activities", [])
        if activities:
            elder_id = detail.get("elder_id", "ELD_101")
            door_count = 0
            for act in activities:
                # 跳过 open 和 close 都为 None 的记录（无实际时间信息）
                open_time = act.get("open")
                close_time = act.get("close")
                date_str = act.get("date", "")
                # 将中文日期转为 ISO 格式：假设当前年份 2026，"06月15日" → "2026-06-15"
                iso_date = f"2026-{date_str[:2]}-{date_str[3:5]}" if len(date_str) >= 5 else None

                if not open_time and not close_time:
                    # 无开门记录 → 生成一条 close 事件表示当天无活动
                    if iso_date:
                        db.add(DoorEvent(
                            elder_id=elder_id,
                            village_id=1,
                            event_type="close",
                            event_time=f"{iso_date} 00:00",
                            event_date=iso_date,
                        ))
                        door_count += 1
                    continue

                # 有开门时间 → 生成 open 事件
                if iso_date and open_time:
                    db.add(DoorEvent(
                        elder_id=elder_id,
                        village_id=1,
                        event_type="open",
                        event_time=f"{iso_date} {open_time}",
                        event_date=iso_date,
                    ))
                    door_count += 1
                if iso_date and close_time:
                    db.add(DoorEvent(
                        elder_id=elder_id,
                        village_id=1,
                        event_type="close",
                        event_time=f"{iso_date} {close_time}",
                        event_date=iso_date,
                    ))
                    door_count += 1
            print(f"  [OK] {door_count} 条门磁事件")

        # AI 报告种子数据（初版静态文本，后续 M4 覆盖）
        elders = (await db.execute(select(Elder))).scalars().all()
        for e in elders:
            tags = json.loads(e.risk_tags) if e.risk_tags else []
            db.add(HealthReport(
                elder_id=e.elder_id,
                report_month="2026-06",
                risk_tags=json.dumps(tags, ensure_ascii=False),
                ai_summary=f"经系统分析，{e.name}本月整体状况良好。建议保持现有生活习惯，关注季节变化。",
                data_source="手环活动记录 + 门磁数据",
                generated_by="qwen-max",
                created_at="2026-06-15",
            ))
        print(f"  [OK] {len(elders)} 份 AI 报告（种子）")

        await db.commit()
    print(f"\n[DONE] 种子数据全部导入完成！默认密码: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(run())
