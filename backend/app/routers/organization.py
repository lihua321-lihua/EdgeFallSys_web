"""
组织架构接口
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.models import Town, Village, Elder, Device, Account
from app.routers.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/api/v1/admin/organization",
    tags=["组织架构"],
    dependencies=[Depends(require_roles("admin", "super_admin"))],
)


class VillageCreateRequest(BaseModel):
    name: str
    town_id: int


class VillageUpdateRequest(BaseModel):
    name: str


@router.get("/tree")
async def get_tree(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """组织架构树"""
    towns_result = await db.execute(select(Town))
    towns = towns_result.scalars().all()

    tree = []
    for town in towns:
        villages_result = await db.execute(
            select(Village).where(Village.town_id == town.id)
        )
        villages = villages_result.scalars().all()

        children = []
        for v in villages:
            elder_count = (await db.execute(
                select(func.count()).select_from(Elder).where(Elder.village_id == v.id)
            )).scalar() or 0
            device_count = (await db.execute(
                select(func.count()).select_from(Device).where(Device.village_id == v.id)
            )).scalar() or 0
            children.append({
                "id": v.id, "label": v.name,
                "elder_count": elder_count, "device_count": device_count,
            })

        tree.append({"id": town.id, "label": town.name, "children": children})

    return {"code": 200, "data": {"tree": tree}}


@router.post("/villages")
async def create_village(
    req: VillageCreateRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_roles("super_admin")),
):
    """新增村庄"""
    town = (await db.execute(select(Town).where(Town.id == req.town_id))).scalar_one_or_none()
    if not town:
        raise HTTPException(status_code=400, detail="乡镇不存在")

    village = Village(town_id=req.town_id, name=req.name)
    db.add(village)
    await db.flush()
    return {"code": 200, "data": {"id": village.id, "name": village.name}}


@router.put("/villages/{village_id}")
async def update_village(
    village_id: int,
    req: VillageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_roles("super_admin")),
):
    """重命名村庄"""
    village = (await db.execute(select(Village).where(Village.id == village_id))).scalar_one_or_none()
    if not village:
        raise HTTPException(status_code=404, detail="村庄不存在")
    village.name = req.name
    await db.flush()
    return {"code": 200, "data": {"id": village.id, "name": village.name}}


@router.delete("/villages/{village_id}")
async def delete_village(
    village_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_roles("super_admin")),
):
    """删除村庄（仅允许删除无老人、无设备、无账号的空村庄）"""
    village = (await db.execute(select(Village).where(Village.id == village_id))).scalar_one_or_none()
    if not village:
        raise HTTPException(status_code=404, detail="村庄不存在")

    elder_count = (await db.execute(
        select(func.count()).select_from(Elder).where(Elder.village_id == village_id)
    )).scalar() or 0
    if elder_count > 0:
        raise HTTPException(status_code=400, detail=f"该村庄下有 {elder_count} 位老人，无法删除")

    device_count = (await db.execute(
        select(func.count()).select_from(Device).where(Device.village_id == village_id)
    )).scalar() or 0
    if device_count > 0:
        raise HTTPException(status_code=400, detail=f"该村庄下有 {device_count} 台设备，无法删除")

    account_count = (await db.execute(
        select(func.count()).select_from(Account).where(Account.village_id == village_id)
    )).scalar() or 0
    if account_count > 0:
        raise HTTPException(status_code=400, detail=f"该村庄下有 {account_count} 个账号，无法删除")

    await db.delete(village)
    await db.flush()
    return {"code": 200, "data": {"message": "村庄已删除"}}
