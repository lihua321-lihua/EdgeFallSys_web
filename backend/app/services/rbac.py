"""
RBAC 行级数据隔离
依赖 M2 已完成的 village_id 字段
"""
from fastapi import HTTPException

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
