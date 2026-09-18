import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.core.dependencies import get_current_user
from app.api.routes.meetings import celery_app
router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/voice_profile")
async def upload_voice_profile(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a 30-second audio clip to register the logged-in user's voice print.
    """

    # Save uploaded file to a shared location for the worker
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    fd, path = tempfile.mkstemp(dir=upload_dir, suffix=".wav")
    with os.fdopen(fd, "wb") as f:
        shutil.copyfileobj(file.file, f)
            
    # Trigger Celery background task
    celery_app.send_task("process_voice_profile", args=[current_user.id, path])
            
    return {"message": "Voice profile upload successful. Processing in background.", "user_name": current_user.name}
