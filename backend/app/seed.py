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
            # 桂花村（village_id=1）
            ("zhang_grid", "张网格员", "village_grid", 1),
            ("li_doctor", "李村医", "village_doctor", 1),
            # 杨柳村（village_id=2）—— P0 新增，展示多村庄数据隔离
            ("chen_grid", "陈网格员", "village_grid", 2),
            ("zhao_doctor", "赵村医", "village_doctor", 2),
            # 管理层
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
                must_change_password=1,   # 首次登录强制改密码（与前端提示一致）
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
        # P0: 新增 medical_judgment、need_transfer 字段（村医医疗判断专用）
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
                    action_type=a.get("action_type"), remark=a.get("remark"),
                    handler_name=a.get("handler_name"), handle_time=a.get("handle_time"),
                    # P0: 村医医疗判断字段
                    medical_judgment=a.get("medical_judgment"),
                    need_transfer=a.get("need_transfer"),
                ))
            print(f"  [OK] {len(alerts_data)} 条告警（含村医医疗判断记录）")

        # —— 5. 走访任务 ——
        # P0: 按 trigger_reason 关键词分配 task_type
        #   含"健康/血压/血糖/随访/用药/体检" → followup（村医随访类）
        #   其他 → patrol（网格员巡查类）
        FOLLOWUP_KEYWORDS = ("健康", "血压", "血糖", "随访", "用药", "体检", "慢病")
        tasks_data = load_json("tasks.json")
        if tasks_data:
            for t in tasks_data:
                reason = t.get("trigger_reason", "") or ""
                t_type = "followup" if any(k in reason for k in FOLLOWUP_KEYWORDS) else "patrol"
                db.add(VisitTask(
                    task_id=t["task_id"], elder_name=t["elder_name"],
                    elder_id=t.get("elder_id"), trigger_reason=t.get("trigger_reason"),
                    status=t.get("status", "pending"), create_time=t.get("create_time"),
                    feedback=t.get("feedback"),
                    handler_name=t.get("handler_name"), handle_time=t.get("handle_time"),
                    task_type=t_type,
                ))
            print(f"  [OK] {len(tasks_data)} 条走访任务（patrol/followup 按触发原因分配）")

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

        # P0: 智能回填 village_id
        #   Elder/Alert/VisitTask：按 elder_id 前缀分配（ELD_1xx→桂花村1, ELD_2xx→杨柳村2）
        #   Device：按 village_name 分配
        def village_id_by_elder(elder_id):
            """按 elder_id 前缀推断村庄：ELD_1xx→1(桂花村), ELD_2xx→2(杨柳村)"""
            if elder_id and elder_id.startswith("ELD_2"):
                return 2
            return 1  # 默认桂花村

        VILLAGE_NAME_TO_ID = {"桂花村": 1, "杨柳村": 2, "石门村": 3, "桃花村": 4}

        # 回填 Elder
        result = await db.execute(select(Elder))
        for row in result.scalars().all():
            row.village_id = village_id_by_elder(row.elder_id)

        # 回填 Alert
        result = await db.execute(select(Alert))
        for row in result.scalars().all():
            row.village_id = village_id_by_elder(row.elder_id)

        # 回填 VisitTask
        result = await db.execute(select(VisitTask))
        for row in result.scalars().all():
            row.village_id = village_id_by_elder(row.elder_id)

        # 回填 Device（按 village_name）
        result = await db.execute(select(Device))
        for row in result.scalars().all():
            row.village_id = VILLAGE_NAME_TO_ID.get(row.village_name, 1)

        print("  [OK] 回填 village_id（ELD_2xx→杨柳村, 其余→桂花村; Device 按 village_name）")

        # ============ P0 新增：杨柳村告警数据 ============
        # 展示第二村庄的数据隔离：杨柳村网格员/村医仅可见本村数据
        yangliu_alerts = [
            {
                "event_id": "EVT_2026_201", "type": "FALL_DETECTED", "level": "CRITICAL",
                "elder_name": "孙爷爷", "elder_id": "ELD_201",
                "create_time": 1716295000, "status": "pending",
                "title": "发生疑似跌倒！", "location": "院子",
                "ai_diagnosis": "老人在院子摔倒，未检测到起身超过5分钟",
            },
            {
                "event_id": "EVT_2026_202", "type": "INTRUSION_ALERT", "level": "HIGH",
                "elder_name": "吴大爷", "elder_id": "ELD_203",
                "create_time": 1716290000, "status": "pending",
                "title": "夜间异常活动预警", "location": "厨房",
                "ai_diagnosis": "凌晨3点检测到厨房异常移动",
            },
            {
                "event_id": "EVT_2026_203", "type": "FALL_DETECTED", "level": "CRITICAL",
                "elder_name": "周奶奶", "elder_id": "ELD_202",
                "create_time": 1716190000, "status": "resolved",
                "action_type": "MEDICAL_JUDGE",
                "medical_judgment": "老人糖尿病低血糖导致晕厥跌倒。现场测血糖 3.2mmol/L，已口服糖水，15分钟后复测 4.8mmol/L 恢复意识。调整胰岛素剂量，无需送医。",
                "need_transfer": 0,
                "handler_name": "赵村医", "handle_time": 1716191200,
                "title": "发生疑似跌倒！", "location": "卧室",
                "ai_diagnosis": "检测到突然倒地",
            },
            {
                "event_id": "EVT_2026_204", "type": "SCAM_ALERT", "level": "HIGH",
                "elder_name": "孙爷爷", "elder_id": "ELD_201",
                "create_time": 1716090000, "status": "resolved",
                "action_type": "VISITED",
                "remark": "上门确认老人接到保健品推销电话，已劝阻并提醒谨防诈骗，协助安装反诈APP。",
                "handler_name": "陈网格员", "handle_time": 1716090800,
                "title": "诈骗电话预警", "location": "客厅",
                "ai_diagnosis": "陌生号码长时间通话",
            },
        ]
        for a in yangliu_alerts:
            db.add(Alert(
                event_id=a["event_id"], type=a["type"], level=a["level"],
                elder_name=a["elder_name"], elder_id=a["elder_id"],
                status=a["status"], create_time=a["create_time"],
                location=a.get("location"), ai_diagnosis=a.get("ai_diagnosis"),
                title=a.get("title"), action_type=a.get("action_type"),
                remark=a.get("remark"), medical_judgment=a.get("medical_judgment"),
                need_transfer=a.get("need_transfer"),
                handler_name=a.get("handler_name"), handle_time=a.get("handle_time"),
                village_id=2,
            ))
        print(f"  [OK] {len(yangliu_alerts)} 条杨柳村告警（展示数据隔离）")

        # ============ P0 新增：杨柳村走访任务 ============
        yangliu_tasks = [
            {
                "task_id": "TASK-201", "elder_name": "孙爷爷", "elder_id": "ELD_201",
                "trigger_reason": "村医慢病随访：老人高血压用药不规律，需上门监测血压并指导用药。",
                "status": "pending", "create_time": "2026-05-21 09:00", "task_type": "followup",
            },
            {
                "task_id": "TASK-202", "elder_name": "吴大爷", "elder_id": "ELD_203",
                "trigger_reason": "网格员巡查：独居老人设备离线超过24小时，需上门确认老人安全。",
                "status": "pending", "create_time": "2026-05-22 08:00", "task_type": "patrol",
            },
            {
                "task_id": "TASK-203", "elder_name": "周奶奶", "elder_id": "ELD_202",
                "trigger_reason": "村医健康体检：老人糖尿病血糖波动大，需上门采血检测糖化血红蛋白。",
                "status": "pending", "create_time": "2026-05-22 14:00", "task_type": "followup",
            },
            {
                "task_id": "TASK-204", "elder_name": "吴大爷", "elder_id": "ELD_203",
                "trigger_reason": "网格员巡查：老人反映家中照明损坏，需协调更换灯泡并检查用电安全。",
                "status": "completed", "create_time": "2026-05-15 10:00", "task_type": "patrol",
                "feedback": "已协调电工更换客厅灯泡，检查线路无老化，用电安全正常",
                "handler_name": "陈网格员", "handle_time": "2026-05-15 11:30",
            },
            {
                "task_id": "TASK-205", "elder_name": "孙爷爷", "elder_id": "ELD_201",
                "trigger_reason": "村医随访：老人血压控制不佳，需调整用药方案并记录血压变化。",
                "status": "completed", "create_time": "2026-05-10 14:00", "task_type": "followup",
                "feedback": "血压 160/95，已将硝苯地平片加量至每日2次，嘱低盐饮食，下周复测",
                "handler_name": "赵村医", "handle_time": "2026-05-10 15:20",
            },
        ]
        for t in yangliu_tasks:
            db.add(VisitTask(
                task_id=t["task_id"], elder_name=t["elder_name"], elder_id=t["elder_id"],
                trigger_reason=t["trigger_reason"], status=t["status"],
                create_time=t["create_time"], feedback=t.get("feedback"),
                handler_name=t.get("handler_name"), handle_time=t.get("handle_time"),
                task_type=t["task_type"], village_id=2,
            ))
        print(f"  [OK] {len(yangliu_tasks)} 条杨柳村走访任务（patrol/followup 各含）")

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
