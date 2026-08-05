"""
RBAC 行级数据隔离 + 角色-资源-操作三级权限控制
依赖 M2 已完成的 village_id 字段
P0 扩展：新增 require_permission 装饰器，支持权限矩阵校验
"""
from fastapi import Depends, HTTPException

from app.routers.auth import get_current_user

# 可查看全量数据的角色
ADMIN_ROLES = ("admin", "super_admin")


def apply_village_filter(query, model, user):
    """
    自动添加 village_id 过滤条件。
    前提：model 必须有 village_id 字段（M2 已完成）。
    """
    if user.role in ADMIN_ROLES:
        return query
    if not user.village_id:
        return query  # 无村庄归属的用户不过滤
    if hasattr(model, 'village_id'):
        return query.where(model.village_id == user.village_id)
    return query


def check_village_access(resource_village_id: int | None, user):
    """
    校验单条资源的 village_id 是否与用户匹配。
    用于详情接口（get_elder、get_ai_report 等）。
    不匹配时抛出 404（而非 403，避免泄露资源存在信息）。
    """
    if user.role in ADMIN_ROLES:
        return  # 管理员无限制
    if not user.village_id:
        return
    if resource_village_id != user.village_id:
        raise HTTPException(status_code=404, detail="资源不存在")


# ==================== P0: 权限矩阵三级控制 ====================
# 内置权限矩阵（角色 × 资源 × 操作）
# 后续可由超级管理员通过 PermissionMatrix 表动态覆盖
DEFAULT_PERMISSIONS = {
    # 告警处理：网格员仅现场处置，村医仅医疗判断，管理员转派
    ("village_grid", "alert", "resolve_field"): True,        # 现场处置
    ("village_grid", "alert", "resolve_medical"): False,     # 医疗判断
    ("village_grid", "alert", "transfer"): False,            # 转派
    ("village_doctor", "alert", "resolve_field"): False,
    ("village_doctor", "alert", "resolve_medical"): True,
    ("village_doctor", "alert", "transfer"): False,
    ("admin", "alert", "resolve_field"): False,
    ("admin", "alert", "resolve_medical"): False,
    ("admin", "alert", "transfer"): True,
    ("super_admin", "alert", "resolve_field"): False,
    ("super_admin", "alert", "resolve_medical"): False,
    ("super_admin", "alert", "transfer"): True,

    # 走访任务：网格员执行巡查类，村医执行随访类
    ("village_grid", "task", "execute_patrol"): True,
    ("village_grid", "task", "execute_followup"): False,
    ("village_doctor", "task", "execute_patrol"): False,
    ("village_doctor", "task", "execute_followup"): True,

    # 医疗数据：仅村医可写
    ("village_grid", "health", "write"): False,
    ("village_doctor", "health", "write"): True,
    ("admin", "health", "write"): False,
    ("super_admin", "health", "write"): False,

    # 采集数据：仅网格员可写
    ("village_grid", "patrol", "write"): True,
    ("village_doctor", "patrol", "write"): False,
    ("admin", "patrol", "write"): False,
    ("super_admin", "patrol", "write"): False,

    # 系统配置：仅超管可写
    ("village_grid", "system_config", "write"): False,
    ("village_doctor", "system_config", "write"): False,
    ("admin", "system_config", "write"): False,
    ("super_admin", "system_config", "write"): True,
}


def has_permission(role: str, resource: str, action: str) -> bool:
    """校验角色是否拥有对指定资源的操作权限。

    优先查 PermissionMatrix 表（动态配置），回退到 DEFAULT_PERMISSIONS（内置默认）。
    P0 阶段暂用内置默认；P2 阶段接入数据库表后可动态调整。
    """
    # P0：直接使用内置默认权限矩阵
    # P2 TODO: 查询 PermissionMatrix 表覆盖默认值
    return DEFAULT_PERMISSIONS.get((role, resource, action), False)


def require_permission(resource: str, action: str):
    """权限矩阵依赖工厂。校验当前用户是否拥有对指定资源的操作权限。

    与 require_roles（粗粒度角色校验）互补，提供细粒度"资源×操作"控制。

    用法：
        @router.post("/{event_id}/resolve-field",
            dependencies=[Depends(require_permission("alert", "resolve_field"))])
        async def resolve_field(...): ...
    """
    async def _check_permission(user=Depends(get_current_user)):
        if not has_permission(user.role, resource, action):
            raise HTTPException(
                status_code=403,
                detail=f"权限不足：角色 '{user.role}' 无权执行 {resource}.{action}",
            )
        return user
    return _check_permission
