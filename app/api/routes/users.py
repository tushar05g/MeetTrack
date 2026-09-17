import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.services.biometrics import extract_voice_embedding
from app.core.dependencies import get_current_user

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

    # Save uploaded file to a temporary location
    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        # Extract the embedding
        try:
            embedding = extract_voice_embedding(path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process audio: {str(e)}")
            
        # Save embedding to user
        # In pgvector, we can assign a numpy array or a list directly to the Vector column
        current_user.voice_embedding = embedding
        db.commit()
        
    finally:
        if os.path.exists(path):
            os.remove(path)
            
    return {"message": "Voice profile registered successfully", "user_name": current_user.name}
