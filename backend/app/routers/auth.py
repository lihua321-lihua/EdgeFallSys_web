"""
认证与权限 - JWT登录签发、Token校验、RBAC角色权限中间件
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext

from app.database import get_db
from app.models import Account, Village, PasswordResetRequest
from app.config import settings
from app.schemas import LoginRequest, ChangePasswordRequest, ForgotPasswordRequest

router = APIRouter(prefix="/api/v1/admin/auth", tags=["认证"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_jwt(user_id: int, role: str, village_id: int | None, remember: bool = False) -> str:
    """生成 JWT Token。remember=True 时有效期延长至 jwt_remember_expire_days 天。"""
    if remember:
        delta = timedelta(days=settings.jwt_remember_expire_days)
    else:
        delta = timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "village_id": village_id,
        "remember": remember,
        "exp": datetime.now(timezone.utc) + delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. 查用户
    result = await db.execute(select(Account).where(Account.username == req.username))
    account = result.scalar_one_or_none()

    if not account or not pwd_context.verify(req.password, account.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if account.status == "disabled":
        raise HTTPException(status_code=401, detail="账号已被禁用")

    # 1.5 校验所选身份与账号实际角色一致，防止越权选择其它身份登录
    if req.roleHint and req.roleHint != account.role:
        raise HTTPException(
            status_code=403,
            detail=f"所选身份与该账号角色不符（账号角色：{account.role}），请重新选择",
        )

    # 2. 签发 Token（remember 控制有效期：勾选→长有效期，未勾选→短有效期）
    token = create_jwt(account.id, account.role, account.village_id, req.remember)

    # 3. 返回（字段名与前端 useAuthStore.js 完全对齐）
    return {
        "code": 200,
        "data": {
            "token": token,
            "must_change_password": bool(account.must_change_password),
            "user": {
                "id": account.id,
                "username": account.username,
                "display_name": account.display_name,   # 前端读 res.user.display_name
                "role": account.role,
                "village_id": account.village_id,
                "village_name": (lambda v: v.name if v else None)(
                    (await db.execute(select(Village).where(Village.id == account.village_id))).scalar_one_or_none()
                ) if account.village_id else None,
            },
        },
    }


async def get_current_user(
    authorization: str = Header(None, description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> Account:
    """JWT 认证依赖注入。从 Authorization 头提取 Token，解析后返回用户对象。
    其他业务路由通过 Depends(get_current_user) 即可获得当前登录用户并强制鉴权。
    """
    # 1. 提取 Token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或 Token 格式错误")
    token = authorization[7:]

    # 2. 解析 Token
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token 无效，请重新登录")

    # 3. 查用户（Token 中的 sub 是 user_id）
    user_id = int(payload.get("sub", 0))
    result = await db.execute(select(Account).where(Account.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.status == "disabled":
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")

    # 检查 Redis 中的禁用标记
    try:
        from app.services.redis_client import get_redis
        r = await get_redis()
        if await r.exists(f"user_disabled:{user_id}"):
            raise HTTPException(status_code=401, detail="账号已被禁用，请联系管理员")
    except HTTPException:
        raise
    except Exception:
        pass

    return user


# ==================== RBAC 角色校验 ====================

# 角色层级：super_admin > admin > village_doctor / village_grid
ROLE_HIERARCHY = {
    "super_admin": 100,
    "admin": 50,
    "village_doctor": 10,
    "village_grid": 10,
}


def require_roles(*allowed_roles: str):
    """RBAC 权限依赖工厂。返回一个 Depends 可用的函数，校验当前用户角色是否在允许列表中。

    用法：
        @router.get("/admin/data", dependencies=[Depends(require_roles("admin", "super_admin"))])
        async def admin_only(user=Depends(get_current_user)): ...

    或者直接在路由函数参数中使用：
        async def admin_api(user: Account = Depends(require_roles("admin", "super_admin"))): ...
    """
    async def _check_role(user: Account = Depends(get_current_user)) -> Account:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"权限不足：当前角色 '{user.role}'，需要 {'/'.join(allowed_roles)}",
            )
        return user
    return _check_role


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    """登出：前端清除本地 Token 即可。"""
    return {"code": 200, "data": {"message": "已登出"}}


# ==================== 密码管理 ====================

@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: Account = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自助修改密码 —— 所有登录用户可用。
    校验原密码后更新为新密码，并清除 must_change_password 标记。"""
    if not pwd_context.verify(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if req.old_password == req.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = pwd_context.hash(req.new_password)
    user.must_change_password = 0
    await db.flush()
    return {"code": 200, "data": {"message": "密码修改成功"}}


@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """忘记密码 —— 不发邮件、不直接重置（账号由管理员统一分配，无邮箱采集）。
    若用户名存在则记录一条重置申请（管理员在「组织架构」页可见并处理）；
    无论用户名是否存在均返回相同文案，避免用户名枚举。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account = (await db.execute(select(Account).where(Account.username == req.username))).scalar_one_or_none()
    if account:
        db.add(PasswordResetRequest(
            account_id=account.id,
            username=account.username,
            display_name=account.display_name,
            requested_at=now,
            status="pending",
        ))
        await db.flush()
    return {
        "code": 200,
        "data": {
            "message": f"重置申请已提交，请联系管理员处理。管理员重置后初始密码为 {settings.default_password}，登录后请及时修改。"
        },
    }
