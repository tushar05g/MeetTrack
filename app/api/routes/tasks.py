from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import SessionLocal
from app.models import Task, TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class TaskUpdateStatus(BaseModel):
    status: TaskStatus

@router.get("")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
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
def update_task_status(task_id: int, update: TaskUpdateStatus, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = update.status
    db.commit()
    return {"status": "success", "task_id": task_id, "new_status": task.status.value}
