"""
账号管理 - 账号列表（村庄筛选）、新增账号、编辑账号、启用/禁用、重置密码
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Account, Village
from app.routers.auth import get_current_user, require_roles, pwd_context
from app.schemas import CreateAccountRequest, UpdateAccountRequest, ToggleAccountRequest

router = APIRouter(
    prefix="/api/v1/admin/accounts",
    tags=["账号管理"],
    dependencies=[Depends(require_roles("admin", "super_admin"))],
)


async def _get_village_name(db: AsyncSession, village_id: int | None) -> str | None:
    """从 Village 表查询村庄名称"""
    if not village_id:
        return None
    v = (await db.execute(select(Village).where(Village.id == village_id))).scalar_one_or_none()
    return v.name if v else None


@router.get("")
async def list_accounts(
    village_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """账号列表。前端 Organization.vue 期望 data 包含 items + total"""
    query = select(Account).order_by(Account.id)
    if village_id is not None:
        query = query.where(Account.village_id == village_id)

    result = await db.execute(query)
    accounts = result.scalars().all()

    items = []
    for a in accounts:
        items.append({
            "id": a.id,
            "username": a.username,
            "display_name": a.display_name,
            "role": a.role,
            "village_id": a.village_id,
            "village_name": await _get_village_name(db, a.village_id),
            "status": a.status,
            "disabled": a.status == "disabled",
        })

    return {"code": 200, "data": {"items": items, "total": len(items)}}


@router.post("")
async def create_account(
    req: CreateAccountRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """新增账号"""
    existing = await db.execute(select(Account).where(Account.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    if req.role in ("admin", "super_admin") and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可创建管理员账号")

    account = Account(
        username=req.username,
        password_hash=pwd_context.hash(req.password),
        display_name=req.display_name,
        role=req.role,
        village_id=req.village_id,
        status="active",
    )
    db.add(account)
    await db.flush()

    return {
        "code": 200,
        "data": {
            "id": account.id,
            "username": account.username,
            "display_name": account.display_name,
            "role": account.role,
            "village_id": account.village_id,
            "village_name": await _get_village_name(db, account.village_id),
            "status": account.status,
        },
    }


@router.put("/{account_id}")
async def update_account(
    account_id: int,
    req: UpdateAccountRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """编辑账号信息"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if req.role and req.role in ("admin", "super_admin") and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可分配管理员角色")

    if account.id == user.id and req.role and req.role != user.role:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    if req.display_name is not None:
        account.display_name = req.display_name
    if req.role is not None:
        account.role = req.role
    if req.village_id is not None:
        account.village_id = req.village_id
    if req.password is not None:
        account.password_hash = pwd_context.hash(req.password)

    await db.flush()

    return {
        "code": 200,
        "data": {
            "id": account.id,
            "username": account.username,
            "display_name": account.display_name,
            "role": account.role,
            "village_id": account.village_id,
            "village_name": await _get_village_name(db, account.village_id),
            "status": account.status,
        },
    }


@router.patch("/{account_id}/status")
async def toggle_account_status(
    account_id: int,
    req: ToggleAccountRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """启用/禁用账号"""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.id == user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己的账号")

    if account.role in ("admin", "super_admin") and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可禁用管理员账号")

    account.status = req.status
    await db.flush()

    # Redis 禁用/启用标记
    if req.status == "disabled":
        try:
            from app.services.redis_client import get_redis
            from app.config import settings
            r = await get_redis()
            expire_seconds = settings.jwt_expire_minutes * 60
            await r.setex(f"user_disabled:{account.id}", expire_seconds, "1")
        except Exception:
            pass
    elif req.status == "active":
        try:
            from app.services.redis_client import get_redis
            r = await get_redis()
            await r.delete(f"user_disabled:{account.id}")
        except Exception:
            pass

    return {"code": 200, "data": {"id": account.id, "status": account.status}}


@router.post("/{account_id}/reset-password")
async def reset_password(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_roles("super_admin")),
):
    """重置密码。返回明文新密码，由前端展示给管理员。"""
    account = (await db.execute(select(Account).where(Account.id == account_id))).scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    new_password = secrets.token_urlsafe(8)
    account.password_hash = pwd_context.hash(new_password)
    await db.flush()

    return {"code": 200, "data": {"id": account.id, "new_password": new_password}}
