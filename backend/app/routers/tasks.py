"""
走访任务 - 任务列表（按状态+角色筛选）、提交走访反馈
P0 修正：网格员仅执行巡查类(patrol)任务，村医仅执行随访类(followup)任务
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import VisitTask
from app.routers.auth import get_current_user, require_roles
from app.schemas import FeedbackRequest
from app.services.rbac import apply_village_filter, check_village_access, has_permission

router = APIRouter(
    prefix="/api/v1/admin/tasks/visits",
    tags=["走访任务"],
    dependencies=[Depends(require_roles("village_grid", "village_doctor", "admin", "super_admin"))],
)

# P0: 角色-任务类型映射
# 网格员执行巡查类任务，村医执行随访类任务（C-01/C-02/C-03 一端一责原则）
ROLE_TASK_TYPE = {
    "village_grid": "patrol",
    "village_doctor": "followup",
}


@router.get("")
async def list_tasks(
    status: str = "",
    task_type: str = "",
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """前端 VisitTasks.vue:99: tasks.value = res.items || []

    P0: 按角色自动过滤任务类型
    - 网格员仅见巡查类(patrol)任务
    - 村医仅见随访类(followup)任务
    - 管理员/超管可见全部（可通过 task_type 参数筛选）
    """
    query = select(VisitTask)
    if status in ("pending", "completed"):
        query = query.where(VisitTask.status == status)

    # P0: L1 角色按 task_type 自动过滤
    if user.role in ROLE_TASK_TYPE:
        query = query.where(VisitTask.task_type == ROLE_TASK_TYPE[user.role])
    elif task_type in ("patrol", "followup"):
        # 管理员/超管可显式筛选
        query = query.where(VisitTask.task_type == task_type)

    query = apply_village_filter(query, VisitTask, user)  # Phase 2: RBAC 行级隔离
    query = query.order_by(VisitTask.create_time.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    items = [
        {
            "task_id": t.task_id,
            "elder_name": t.elder_name,
            "elder_id": t.elder_id,
            "trigger_reason": t.trigger_reason,
            "status": t.status,
            "create_time": t.create_time,
            "feedback": t.feedback,
            "handler_name": t.handler_name,        # 处理人
            "handle_time": t.handle_time,          # 处理完成时间（"YYYY-MM-DD HH:MM"）
            "task_type": t.task_type,              # P0: patrol/followup
        }
        for t in tasks
    ]
    return {"code": 200, "data": {"items": items, "total": len(items)}}


@router.post("/{task_id}/feedback")
async def submit_feedback(
    task_id: str,
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """提交走访反馈 - P0 角色与任务类型一致性校验

    网格员仅可提交巡查类任务反馈，村医仅可提交随访类任务反馈。
    """
    result = await db.execute(select(VisitTask).where(VisitTask.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="走访任务不存在")
    check_village_access(task.village_id, user)
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="任务已完成，不可重复提交")

    # P0: 角色与任务类型一致性校验
    if user.role in ROLE_TASK_TYPE:
        expected_type = ROLE_TASK_TYPE[user.role]
        if task.task_type != expected_type:
            role_label = "网格员" if user.role == "village_grid" else "村医"
            type_label = "巡查类" if expected_type == "patrol" else "随访类"
            raise HTTPException(
                status_code=403,
                detail=f"{role_label}仅可执行{type_label}任务，当前任务类型为 '{task.task_type}'",
            )
        # 权限矩阵二次校验
        action = "execute_patrol" if expected_type == "patrol" else "execute_followup"
        if not has_permission(user.role, "task", action):
            raise HTTPException(status_code=403, detail=f"权限不足：无执行{action}权限")
    elif user.role in ("admin", "super_admin"):
        # 管理员不执行具体走访任务（C-04 管理不下沉）
        raise HTTPException(status_code=403, detail="管理员不执行走访任务，仅可派发和查看")

    task.status = "completed"
    task.feedback = req.feedback
    task.handler_name = user.display_name                       # 处理人 = 当前登录账号
    task.handle_time = datetime.now().strftime("%Y-%m-%d %H:%M")  # 处理完成时间
    await db.flush()

    return {"code": 200, "data": {"message": "反馈提交成功"}}
