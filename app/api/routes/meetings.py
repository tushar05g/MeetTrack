import os
import shutil
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import SessionLocal
from app.models import Meeting, MeetingStatus, Task, TaskStatus, Transcript
from app.worker import process_meeting
import csv
import io
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

@router.post("/bot/join")
def join_live_meeting(
    meet_url: str = Form(...),
    duration_seconds: int = Form(60),
    scheduled_time: str = Form(None),
    participants_csv: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if not meet_url:
        raise HTTPException(status_code=400, detail="Missing Google Meet URL")
    
    parsed_time = None
    if scheduled_time:
        parsed_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00').split('.')[0])
        
    meeting = Meeting(
        title=f"Live Meeting: {meet_url.split('/')[-1]}",
        audio_file_path="", 
        status=MeetingStatus.scheduled if parsed_time else MeetingStatus.pending,
        scheduled_time=parsed_time,
        meet_url=meet_url,
        bot_duration=duration_seconds
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Process CSV if provided
    if participants_csv:
        content = participants_csv.file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        
        # Try to find name and email columns gracefully
        fieldnames = [f.lower().strip() for f in (reader.fieldnames or [])]
        name_col = next((f for f in reader.fieldnames if f.lower().strip() in ["name", "full name", "participant"]), None)
        email_col = next((f for f in reader.fieldnames if f.lower().strip() in ["email", "e-mail", "email address"]), None)

        from app.models import MeetingParticipant
        if name_col and email_col:
            for row in reader:
                name = row.get(name_col, "").strip()
                email = row.get(email_col, "").strip()
                if name and email:
                    mp = MeetingParticipant(meeting_id=meeting.id, name=name, email=email)
                    db.add(mp)
            db.commit()
    
    if parsed_time:
        return {"message": "Meeting scheduled successfully", "meeting_id": meeting.id, "scheduled": True}
    else:
        from app.worker import run_bot_and_process
        run_bot_and_process.delay(meeting.id, meet_url, duration_seconds)
        return {"message": "Bot dispatched to meeting", "meeting_id": meeting.id, "scheduled": False}

@router.post("/upload")
async def upload_meeting(
    file: UploadFile = File(...), 
    recorded_date: date = Form(default_factory=date.today),
    db: Session = Depends(get_db)
):
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
        recorded_date=recorded_date,
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
            "created_at": m.created_at.isoformat() + "Z" if m.created_at else None
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
        "created_at": meeting.created_at.isoformat() + "Z" if meeting.created_at else None,
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
