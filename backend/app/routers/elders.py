"""
老人档案 - 老人列表（分页+模糊搜索）、老人详情、AI健康评估报告
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.database import get_db
from app.models import Elder
from app.routers.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/api/v1/admin/elders",
    tags=["老人档案"],
    dependencies=[Depends(require_roles("village_grid", "village_doctor", "admin", "super_admin"))],
)


@router.get("")
async def list_elders(
    keyword: str = "",
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """老人名册。前端 ElderRoster.vue:105: res.items"""
    query = select(Elder)
    if keyword:
        query = query.where(
            (Elder.name.contains(keyword)) | (Elder.address.contains(keyword))
        )

    # 总数
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # 分页
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    elders = result.scalars().all()

    items = []
    for e in elders:
        tags = json.loads(e.risk_tags) if e.risk_tags else []
        items.append({
            "elder_id": e.elder_id, "name": e.name, "age": e.age,
            "gender": e.gender, "address": e.address,
            "device_sn": e.device_sn, "gateway_sn": e.gateway_sn,
            "emergency_contact": e.emergency_contact, "risk_tags": tags,
        })

    return {"code": 200, "data": {"items": items, "total": total}}


@router.get("/{elder_id}")
async def get_elder(
    elder_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """老人详情。前端 ElderDetail.vue:166: elder.value = detailRes.value"""
    result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
    e = result.scalar_one_or_none()

    if not e:
        raise HTTPException(status_code=404, detail="老人不存在")

    return {
        "code": 200,
        "data": {
            "elder_id": e.elder_id, "name": e.name, "age": e.age,
            "gender": e.gender, "address": e.address,
            "device_sn": e.device_sn, "gateway_sn": e.gateway_sn,
            "emergency_contact": e.emergency_contact,
            "emergency_relation": e.emergency_relation,
            "medical_history": e.medical_history,
            "bind_duration": e.bind_duration,
            "recent_activities": [
                {"date": "06月15日", "open": "08:15", "close": "09:30", "status": "normal"},
                {"date": "06月14日", "open": None, "close": None, "status": "warning"},
                {"date": "06月13日", "open": None, "close": None, "status": "warning"},
                {"date": "06月12日", "open": None, "close": None, "status": "danger"},
                {"date": "06月11日", "open": "10:00", "close": "11:20", "status": "normal"},
            ],
        },
    }


@router.get("/{elder_id}/ai-report")
async def get_ai_report(
    elder_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """AI 健康报告。前端 ElderDetail.vue:169: aiReport.value = reportRes.value
    MVP 阶段返回静态文本，Phase 2 改为调用大模型生成"""

    result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
    e = result.scalar_one_or_none()

    tags = json.loads(e.risk_tags) if e and e.risk_tags else []

    return {
        "code": 200,
        "data": {
            "report_date": "2026-06",
            "risk_tags": tags,
            "ai_summary": "经系统分析，本月老人情绪状态尚可，步态平稳度正常。外出活动量较上月略有增加，社交活跃度良好。建议继续保持日常活动习惯，关注天气变化对关节的影响。",
            "data_source": "手环UWB轨迹 + 门磁活动记录",
        },
    }
