import os
import shutil
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models import Meeting, MeetingStatus, Task, TaskStatus, Transcript
from app.worker import process_meeting
from pydantic import BaseModel

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

@router.post("/upload")
async def upload_meeting(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Generate unique filename using original filename safely
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Create meeting record in DB
    meeting = Meeting(
        title=file.filename,
        audio_file_path=file_path,
        status=MeetingStatus.pending
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    # Trigger Celery background task
    process_meeting.delay(meeting.id)
    
    return {"message": "Meeting uploaded successfully", "meeting_id": meeting.id}

@router.get("")
def list_meetings(db: Session = Depends(get_db)):
    meetings = db.query(Meeting).order_by(desc(Meeting.created_at)).all()
    
    return [
        {
            "id": m.id,
            "title": m.title,
            "status": m.status.value,
            "created_at": m.created_at
        } for m in meetings
    ]

@router.get("/{meeting_id}")
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    response = {
        "id": meeting.id,
        "title": meeting.title,
        "status": meeting.status.value,
        "created_at": meeting.created_at,
        "transcript": None,
        "tasks": []
    }
    
    if meeting.transcript:
        response["transcript"] = {
            "full_text": meeting.transcript.full_text,
            "segments": meeting.transcript.segments
        }
        
    if meeting.tasks:
        response["tasks"] = [
            {
                "id": t.id,
                "description": t.description,
                "owner": t.owner.name if hasattr(t, 'owner') and t.owner else None, 
                "deadline": t.deadline,
                "status": t.status.value
            } for t in meeting.tasks
        ]
        
    return response

class MapSpeakerRequest(BaseModel):
    speaker_label: str
    real_name: str

@router.post("/{meeting_id}/map_speaker")
def map_speaker(meeting_id: int, request: MapSpeakerRequest, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # UI-level mapping placeholder logic
    return {"status": "success", "message": f"Mapped {request.speaker_label} to {request.real_name}"}
