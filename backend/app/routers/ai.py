"""
AI 路由 - 大模型调用入口（告警分类 / 流式对话 / 监控 / 健康报告）

所有数据经 ai_service 记账（LlmCallLog 明细 + ApiUsage 聚合 + Redis 计数），
监控台展示的数据均来源于真实调用，无假数据。
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Elder, HealthReport, LlmCallLog, AiAnalysisReport
from app.routers.auth import get_current_user, require_roles
from app.schemas import RescueBriefingRequest, HealthAnalysisRequest, FullAnalysisRequest
from app.services import ai_service

router = APIRouter(
    prefix="/api/v1/admin/ai",
    tags=["AI 大模型"],
    dependencies=[Depends(require_roles("admin", "super_admin", "village_grid", "village_doctor"))],
)


# ========== 请求模型 ==========

class ClassifyAlertRequest(BaseModel):
    alert_type: str = Field(..., description="FALL_DETECTED / SCAM_ALERT / INTRUSION_ALERT 等")
    alert_text: str = ""
    elder_context: str = ""
    event_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[list[ChatMessage]] = None


# ========== 告警智能分类 ==========

@router.post("/classify-alert")
async def classify_alert(
    req: ClassifyAlertRequest,
    db: AsyncSession = Depends(get_db),
):
    """对告警文本进行智能分类，返回 {category, severity, suggestion}。

    Key 未配置/超限/失败均降级为规则分类，不报错。
    """
    result = await ai_service.classify_alert(
        db,
        alert_type=req.alert_type,
        alert_text=req.alert_text,
        elder_context=req.elder_context,
        request_id=req.event_id,
    )
    return {"code": 200, "data": result}


# ========== 流式对话（SSE） ==========

@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式对话。前端用原生 fetch + ReadableStream 接收。

    响应 Content-Type: text/event-stream，每条形如 'data: {"text":"..."}\\n\\n'，
    末尾 'data: [DONE]\\n\\n'。
    """
    history = [m.model_dump() for m in req.history] if req.history else None

    async def gen():
        async for chunk in ai_service.stream_chat(db, req.message, history):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ========== 监控数据 ==========

@router.get("/monitor")
async def get_monitor(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    """大模型服务监控：最近调用明细 + 汇总 + 按天趋势。

    数据全部来自 LlmCallLog 真实记录。
    """
    days = max(1, min(days, 90))
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    # 1. 最近 20 条调用明细
    recent = (await db.execute(
        select(LlmCallLog).order_by(LlmCallLog.id.desc()).limit(20)
    )).scalars().all()
    recent_calls = [
        {
            "id": r.id,
            "endpoint": r.endpoint,
            "model": r.model,
            "status": r.status,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "latency_ms": r.latency_ms,
            "cost_cny": round(r.cost_cny or 0, 4),
            "error_msg": r.error_msg,
            "created_at": r.created_at,
        }
        for r in recent
    ]

    # 2. 汇总（今日）
    today_stats = (await db.execute(
        select(
            func.count(LlmCallLog.id),
            func.sum(LlmCallLog.total_tokens),
            func.avg(LlmCallLog.latency_ms),
        ).where(LlmCallLog.created_date == today)
    )).one()
    today_total = today_stats[0] or 0
    today_tokens = today_stats[1] or 0
    today_avg_latency = int(today_stats[2] or 0)

    today_success = (await db.execute(
        select(func.count(LlmCallLog.id)).where(
            LlmCallLog.created_date == today,
            LlmCallLog.status == "success",
        )
    )).scalar() or 0
    today_failed = (await db.execute(
        select(func.count(LlmCallLog.id)).where(
            LlmCallLog.created_date == today,
            LlmCallLog.status.in_(("failed", "degraded", "skipped")),
        )
    )).scalar() or 0
    success_rate = round(today_success / today_total * 100, 1) if today_total else 0.0

    # 3. 按天趋势
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
    trend = [
        {
            "date": row[0],
            "tokens": row[1] or 0,
            "calls": row[2] or 0,
            "avg_latency_ms": int(row[3] or 0),
        }
        for row in trend_rows
    ]

    return {"code": 200, "data": {
        "recent_calls": recent_calls,
        "summary": {
            "today_calls": today_total,
            "today_tokens": today_tokens,
            "today_avg_latency_ms": today_avg_latency,
            "today_success_rate": success_rate,
            "today_error_count": today_failed,
            "qwen_configured": ai_service._is_qwen_configured(),
        },
        "trend": trend,
    }}


# ========== 手动触发健康报告 ==========

@router.post("/health-report/{elder_id}")
async def generate_health_report(
    elder_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """手动为指定老人生成本月 AI 健康报告（经 ai_service 记账）。

    data_summary 综合老人档案 + TDengine 本月手环数据（心率/血氧/步数均值、异常次数）
    + 近期跌倒告警，让大模型生成有监测数据依据的评估，而非固定字样。
    """
    elder = (await db.execute(select(Elder).where(Elder.elder_id == elder_id))).scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")

    month = datetime.now().strftime("%Y-%m")

    # 构造数据摘要：档案 + 本月手环监测数据 + 近期告警（降级友好）
    data_summary = await _build_monthly_data_summary(db, elder)

    # 调用大模型（经 ai_service 记账）
    ai_text = await ai_service.generate_health_report_v2(
        db, elder.name, elder.age or 0, elder.gender or "未知", data_summary,
        request_id=f"manual:{elder_id}:{month}",
    )

    # 覆盖本月报告（若已存在则更新）
    import json
    existing = (await db.execute(
        select(HealthReport).where(
            HealthReport.elder_id == elder_id,
            HealthReport.report_month == month,
        )
    )).scalar_one_or_none()
    tags = json.loads(elder.risk_tags) if elder.risk_tags else []
    if existing:
        existing.ai_summary = ai_text
        existing.generated_by = settings.qwen_model_name
        existing.created_at = datetime.now().isoformat()
    else:
        db.add(HealthReport(
            elder_id=elder_id,
            report_month=month,
            risk_tags=json.dumps(tags, ensure_ascii=False),
            ai_summary=ai_text,
            data_source="手动触发生成",
            generated_by=settings.qwen_model_name,
            created_at=datetime.now().isoformat(),
        ))

    return {"code": 200, "data": {"elder_id": elder_id, "report_month": month, "ai_summary": ai_text}}


# ============================================================
# 专业 AI 分析报告：跌倒救援简报 + 长期健康分析
# ============================================================
# 两类报告均为固定模块结构化 JSON，由大模型生成；断网/Key 未配置/置信度不足/超限
# 时走本地模板兜底。支持连续两次独立调用（先救援简报再健康分析），导出 JSON+TXT 文件。

async def _build_monthly_data_summary(db: AsyncSession, elder: Elder) -> str:
    """构造本月数据摘要：档案 + TDengine 手环数据（心率/血氧/步数均值、异常次数）+ 近期跌倒告警。

    TDengine 不可用时降级为档案信息，保证大模型仍能生成（非固定字样）。
    """
    parts = [f"年龄{elder.age or '未知'}岁，性别{elder.gender or '未知'}，住址{elder.address or '未知'}。"]
    if elder.medical_history:
        parts.append(f"既往病史：{elder.medical_history}。")

    # 本月手环监测数据（降级友好）
    try:
        from app.services.tdengine_client import td_client
        bracelet = await td_client.query_bracelet_recent(elder.elder_id, hours=24 * 30)
        if bracelet:
            hrs = [r.get("heart_rate") for r in bracelet if r.get("heart_rate")]
            spo2s = [r.get("spo2") for r in bracelet if r.get("spo2")]
            steps_list = [r.get("steps") for r in bracelet if r.get("steps") is not None]
            temps = [r.get("temperature") for r in bracelet if r.get("temperature")]
            parts.append(f"本月采集手环数据 {len(bracelet)} 条。")
            if hrs:
                hr_avg = round(sum(hrs) / len(hrs))
                hr_abn = sum(1 for h in hrs if h > 100 or h < 50)
                parts.append(f"心率均值 {hr_avg} bpm，异常 {hr_abn} 次。")
            if spo2s:
                spo2_avg = round(sum(spo2s) / len(spo2s))
                spo2_low = sum(1 for s in spo2s if s < 92)
                parts.append(f"血氧均值 {spo2_avg}%，低于92%共 {spo2_low} 次。")
            if steps_list:
                steps_avg = round(sum(steps_list) / len(steps_list))
                parts.append(f"日均步数 {steps_avg}。")
            if temps:
                t_avg = round(sum(temps) / len(temps), 1)
                parts.append(f"体温均值 {t_avg}℃。")
    except Exception:
        pass  # TDengine 不可用，仅用档案信息

    # 近期跌倒告警次数（Alert.create_time 为 Unix 时间戳）
    try:
        from app.models import Alert
        month_start_ts = int(datetime.now().replace(day=1, hour=0, minute=0, second=0).timestamp())
        fall_count = (await db.execute(
            select(func.count(Alert.event_id)).where(
                Alert.elder_id == elder.elder_id,
                Alert.type == "FALL_DETECTED",
                Alert.create_time >= month_start_ts,
            )
        )).scalar() or 0
        if fall_count:
            parts.append(f"本月发生跌倒告警 {fall_count} 次。")
    except Exception:
        pass

    return "".join(parts)


async def _assemble_health_data(db: AsyncSession, elder: Elder, days: int) -> dict:
    """从老人档案 + TDengine 手环数据组装长期健康分析输入数据。TDengine 不可用时降级为档案信息。"""
    health_data = {
        "data_period": f"近{days}天",
        "medication_records": elder.medical_history or "未提供",
        "past_falls": "未提供",
        "activity_summary": "未提供",
    }
    # 尝试从 TDengine 拉取手环数据（降级友好，失败不影响报告生成）
    try:
        from app.services.tdengine_client import td_client
        bracelet = await td_client.query_bracelet_recent(elder.elder_id, hours=days * 24)
        if bracelet:
            hrs = [r.get("heart_rate") for r in bracelet if r.get("heart_rate")]
            spo2s = [r.get("spo2") for r in bracelet if r.get("spo2")]
            steps_list = [r.get("steps") for r in bracelet if r.get("steps") is not None]
            health_data["hr_history"] = ",".join(str(h) for h in hrs[:50]) if hrs else "无数据"
            health_data["spo2_history"] = ",".join(str(s) for s in spo2s[:50]) if spo2s else "无数据"
            health_data["steps_avg"] = int(sum(steps_list) / len(steps_list)) if steps_list else None
            health_data["activity_summary"] = f"采集到 {len(bracelet)} 条手环数据"
        else:
            health_data["hr_history"] = "无数据（TDengine 无记录或未启用）"
    except Exception as e:
        health_data["hr_history"] = f"无数据（TDengine 不可用: {e}）"

    # 档案补充
    if elder.age:
        health_data["activity_summary"] += f"，年龄{elder.age}岁"
    return health_data


@router.post("/rescue-briefing")
async def rescue_briefing(
    req: RescueBriefingRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """生成跌倒救援简报（9 模块 JSON）。

    置信度 < 0.85 或断网/Key 未配置/超限 → 本地模板兜底（source=fallback）。
    生成后落库 + 导出 JSON/TXT 文件，返回报告与 report_id。
    """
    elder = (await db.execute(select(Elder).where(Elder.elder_id == req.elder_id))).scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")

    # 补充档案信息到 fall_data（前端可只传部分字段）
    fall_data = req.fall_data.model_dump(exclude_none=True)
    if not fall_data.get("medical_history") and elder.medical_history:
        fall_data["medical_history"] = elder.medical_history
    if not fall_data.get("emergency_contact") and elder.emergency_contact:
        fall_data["emergency_contact"] = elder.emergency_contact
    if not fall_data.get("emergency_relation") and elder.emergency_relation:
        fall_data["emergency_relation"] = elder.emergency_relation

    result = await ai_service.generate_rescue_briefing(
        db, elder_id=req.elder_id, fall_data=fall_data,
        request_id=req.event_id or f"rescue:{req.elder_id}:{datetime.now().strftime('%H%M%S')}",
        event_id=req.event_id, confidence=req.confidence,
        force_fallback=req.force_fallback,
    )
    return {"code": 200, "data": result}


@router.post("/health-analysis")
async def health_analysis(
    req: HealthAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """生成长期健康数据分析报告（10 模块 JSON）。

    health_data 未传时由后端从 TDengine + 老人档案组装。Key 未配置/超限 → 本地模板兜底。
    """
    elder = (await db.execute(select(Elder).where(Elder.elder_id == req.elder_id))).scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")

    if req.health_data:
        health_data = req.health_data.model_dump(exclude_none=True)
    else:
        health_data = await _assemble_health_data(db, elder, req.days)

    result = await ai_service.generate_health_analysis(
        db, elder_id=req.elder_id, health_data=health_data,
        request_id=f"health:{req.elder_id}:{datetime.now().strftime('%H%M%S')}",
        force_fallback=req.force_fallback,
    )
    return {"code": 200, "data": result}


@router.post("/full-analysis/{elder_id}")
async def full_analysis(
    elder_id: str,
    req: FullAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """连续两次独立调用：先生成救援简报，再生成健康分析。两次调用互不干扰。

    满足"支持网页后端连续发起两次独立调用（先救援简报、再健康分析）"需求。
    请求体传 fall_data/confidence/days/force_fallback，未传 fall_data 则用档案组装。
    """
    elder = (await db.execute(select(Elder).where(Elder.elder_id == elder_id))).scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")

    ts = datetime.now().strftime("%H%M%S")
    # 第一次独立调用：救援简报
    fd = req.fall_data.model_dump(exclude_none=True) if req.fall_data else {}
    if not fd.get("medical_history") and elder.medical_history:
        fd["medical_history"] = elder.medical_history
    if not fd.get("emergency_contact") and elder.emergency_contact:
        fd["emergency_contact"] = elder.emergency_contact
    if not fd.get("emergency_relation") and elder.emergency_relation:
        fd["emergency_relation"] = elder.emergency_relation

    rescue = await ai_service.generate_rescue_briefing(
        db, elder_id=elder_id, fall_data=fd,
        request_id=f"full-rescue:{elder_id}:{ts}",
        confidence=req.confidence, force_fallback=req.force_fallback,
    )
    # 第二次独立调用：健康分析（独立 request_id，互不干扰）
    health_data = await _assemble_health_data(db, elder, req.days)
    health = await ai_service.generate_health_analysis(
        db, elder_id=elder_id, health_data=health_data,
        request_id=f"full-health:{elder_id}:{ts}",
        force_fallback=req.force_fallback,
    )
    return {"code": 200, "data": {"rescue_briefing": rescue, "health_analysis": health}}


@router.get("/reports")
async def list_reports(
    elder_id: Optional[str] = None,
    report_type: Optional[str] = Query(None, pattern="^(rescue_briefing|health_analysis)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """AI 分析报告列表，可按 elder_id / report_type 过滤。"""
    query = select(AiAnalysisReport).order_by(AiAnalysisReport.id.desc()).limit(limit)
    if elder_id:
        query = query.where(AiAnalysisReport.elder_id == elder_id)
    if report_type:
        query = query.where(AiAnalysisReport.report_type == report_type)
    rows = (await db.execute(query)).scalars().all()
    items = [
        {
            "report_id": r.id,
            "report_type": r.report_type,
            "elder_id": r.elder_id,
            "event_id": r.event_id,
            "source": r.source,
            "confidence": r.confidence,
            "model": r.model,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return {"code": 200, "data": {"items": items, "total": len(items)}}


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """报告详情（JSON + TXT + 元数据）。"""
    r = (await db.execute(
        select(AiAnalysisReport).where(AiAnalysisReport.id == report_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="报告不存在")
    import json as _json
    try:
        report_obj = _json.loads(r.report_json) if r.report_json else {}
    except Exception:
        report_obj = {}
    return {"code": 200, "data": {
        "report_id": r.id,
        "report_type": r.report_type,
        "elder_id": r.elder_id,
        "event_id": r.event_id,
        "report": report_obj,
        "report_txt": r.report_txt,
        "source": r.source,
        "confidence": r.confidence,
        "model": r.model,
        "json_file_path": r.json_file_path,
        "txt_file_path": r.txt_file_path,
        "created_at": r.created_at,
    }}


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    format: str = Query("json", pattern="^(json|txt)$"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """下载报告文件（JSON 或 TXT）。"""
    r = (await db.execute(
        select(AiAnalysisReport).where(AiAnalysisReport.id == report_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="报告不存在")

    file_path = r.json_file_path if format == "json" else r.txt_file_path
    if not file_path:
        raise HTTPException(status_code=404, detail=f"报告无 {format} 文件存档")

    from pathlib import Path
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="存档文件已丢失")

    media = "application/json" if format == "json" else "text/plain; charset=utf-8"
    filename = f"{r.report_type}_{r.elder_id}_{r.id}.{format}"
    return FileResponse(file_path, media_type=media, filename=filename)
