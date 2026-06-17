"""
走访任务 - 任务列表（按状态筛选）、提交走访反馈
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import VisitTask
from app.routers.auth import get_current_user, require_roles
from app.schemas import FeedbackRequest

router = APIRouter(
    prefix="/api/v1/admin/tasks/visits",
    tags=["走访任务"],
    dependencies=[Depends(require_roles("village_grid", "village_doctor", "admin", "super_admin"))],
)


@router.get("")
async def list_tasks(
    status: str = "",
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
):
    """前端 VisitTasks.vue:99: tasks.value = res.items || []"""
    query = select(VisitTask)
    if status in ("pending", "completed"):
        query = query.where(VisitTask.status == status)
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
    result = await db.execute(select(VisitTask).where(VisitTask.task_id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="走访任务不存在")
    if task.status == "completed":
        raise HTTPException(status_code=400, detail="任务已完成，不可重复提交")

    task.status = "completed"
    task.feedback = req.feedback
    await db.flush()

    return {"code": 200, "data": {"message": "反馈提交成功"}}
