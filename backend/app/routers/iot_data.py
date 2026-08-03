"""
IoT 时序数据查询接口
供前端老人详情页展示手环/门磁/UWB 实时数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Elder
from app.routers.auth import get_current_user
from app.services.rbac import check_village_access
from app.services.tdengine_client import td_client

router = APIRouter(prefix="/api/v1/admin/iot", tags=["IoT 时序数据"])


@router.get("/{elder_id}/bracelet")
async def get_bracelet_data(
    elder_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="查询最近 N 小时"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")
    check_village_access(elder.village_id, user)

    data = await td_client.query_bracelet_recent(elder_id, hours=hours)
    return {"code": 200, "data": data}


@router.get("/{elder_id}/door-events")
async def get_door_events(
    elder_id: str,
    days: int = Query(default=7, ge=1, le=90, description="查询最近 N 天"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")
    check_village_access(elder.village_id, user)

    data = await td_client.query_door_events(elder_id, days=days)
    return {"code": 200, "data": data}


@router.get("/{elder_id}/uwb-stats")
async def get_uwb_room_stats(
    elder_id: str,
    days: int = Query(default=7, ge=1, le=90, description="查询最近 N 天"),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(select(Elder).where(Elder.elder_id == elder_id))
    elder = result.scalar_one_or_none()
    if not elder:
        raise HTTPException(status_code=404, detail="老人不存在")
    check_village_access(elder.village_id, user)

    data = await td_client.query_uwb_room_stats(elder_id, days=days)
    return {"code": 200, "data": data}
