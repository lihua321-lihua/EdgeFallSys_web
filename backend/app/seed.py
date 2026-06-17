"""
种子数据脚本 - 从前端Mock JSON读取数据，批量写入SQLite数据库
"""
import json
import asyncio
from pathlib import Path
from passlib.context import CryptContext

from app.database import async_session, init_db
from app.models import Account, Elder, Device, Alert, VisitTask, ApiUsage

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
            print(f"  [OK] API 用量数据")

        await db.commit()
    print(f"\n[DONE] 种子数据全部导入完成！默认密码: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(run())
