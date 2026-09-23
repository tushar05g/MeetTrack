from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import Task, TaskStatus, Meeting, User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])

from app.database import get_db

class TaskUpdateStatus(BaseModel):
    status: TaskStatus

@router.get("")
async def list_tasks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).join(Meeting).filter(Meeting.owner_id == current_user.id).options(joinedload(Task.owner)))
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "meeting_id": t.meeting_id,
            "description": t.description,
            "owner": t.owner.name if hasattr(t, 'owner') and t.owner else None,
            "deadline": t.deadline,
            "status": t.status.value
        } for t in tasks
    ]

@router.patch("/{task_id}")
async def update_task_status(task_id: int, update: TaskUpdateStatus, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Task).join(Meeting).filter(Task.id == task_id, Meeting.owner_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = update.status
    await db.commit()
    return {"status": "success", "task_id": task_id, "new_status": task.status.value}
