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
from app.models import Account
from app.config import settings
from app.schemas import LoginRequest

router = APIRouter(prefix="/api/v1/admin/auth", tags=["认证"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_jwt(user_id: int, role: str, village_id: int | None) -> str:
    """生成 JWT Token，payload 含用户 ID、角色、村庄 ID"""
    payload = {
        "sub": str(user_id),
        "role": role,
        "village_id": village_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
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

    # 2. 签发 Token
    token = create_jwt(account.id, account.role, account.village_id)

    # 3. 返回（字段名与前端 useAuthStore.js 完全对齐）
    return {
        "code": 200,
        "data": {
            "token": token,
            "user": {
                "id": account.id,
                "username": account.username,
                "display_name": account.display_name,   # 前端读 res.user.display_name
                "role": account.role,
                "village_id": account.village_id,
                "village_name": "桂花村" if account.village_id else None,
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
