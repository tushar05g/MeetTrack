import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import User
from app.core.dependencies import get_current_user
from app.api.routes.meetings import celery_app
router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/voice_profile")
async def upload_voice_profile(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a 30-second audio clip to register the logged-in user's voice print.
    """

    # Save uploaded file to Minio
    import time
    from app.core.storage import upload_fileobj_to_s3
    object_name = f"voice_profiles/{current_user.id}_{int(time.time())}.wav"
    s3_uri = upload_fileobj_to_s3(file.file, object_name)
            
    # Trigger Celery background task
    celery_app.send_task("process_voice_profile", args=[current_user.id, s3_uri])
            
    return {"message": "Voice profile upload successful. Processing in background.", "user_name": current_user.name}
