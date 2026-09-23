import os
import shutil
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_

from app.database import SessionLocal
from app.models import Meeting, MeetingStatus, Task, TaskStatus, Transcript, MeetingParticipant, User
from app.core.dependencies import get_current_user
import csv
import io
from pydantic import BaseModel
from celery import Celery

celery_app = Celery(
    "meettrack",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fixed: point to app/uploads/ relative to the project root
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "app", "uploads")

def parse_participants_csv(db: Session, meeting_id: int, participants_csv: UploadFile):
    if not participants_csv:
        return
    try:
        content = participants_csv.file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        
        name_col = next((f for f in reader.fieldnames if f.lower().strip() in ["name", "full name", "participant"]), None)
        email_col = next((f for f in reader.fieldnames if f.lower().strip() in ["email", "e-mail", "email address"]), None)

        from app.models import MeetingParticipant
        if name_col and email_col:
            for row in reader:
                name = row.get(name_col, "").strip()
                email = row.get(email_col, "").strip()
                if name and email:
                    mp = MeetingParticipant(meeting_id=meeting_id, name=name, email=email)
                    db.add(mp)
            db.commit()
    except Exception as e:
        print(f"Failed to parse CSV: {e}")

@router.post("/bot/join")
def join_live_meeting(
    meet_url: str = Form(...),
    
    scheduled_time: str = Form(None),
    bot_email: str = Form(None),
    bot_password: str = Form(None),
    participants_csv: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        bot_duration=None,
        bot_email=bot_email,
        bot_password=bot_password,
        owner_id=current_user.id
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Process CSV if provided
    parse_participants_csv(db, meeting.id, participants_csv)
    
    if parsed_time:
        return {"message": "Meeting scheduled successfully", "meeting_id": meeting.id, "scheduled": True}
    else:
        celery_app.send_task("run_bot_and_process", args=[meeting.id, meet_url])
        return {"message": "Bot dispatched to meeting", "meeting_id": meeting.id, "scheduled": False}

from pydantic import BaseModel
from typing import Optional, Dict, Any

class BotWebhookPayload(BaseModel):
    recordingId: str
    status: str
    meetingLink: Optional[str] = None
    blobUrl: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.post("/bot/webhook")
def bot_webhook(payload: BotWebhookPayload, db: Session = Depends(get_db)):
    """
    Webhook called by screenappai/meeting-bot when it finishes recording.
    """
    print(f"[WEBHOOK] Received payload: {payload.dict()}")

    if payload.status != "completed":
        print(f"[WEBHOOK] Received non-completed status: {payload.status}")
        return {"status": "ignored"}

    # Extract meeting ID. We passed botId as "bot_{meeting_id}"
    bot_id = None
    if payload.metadata and "botId" in payload.metadata:
        bot_id = payload.metadata["botId"]
    else:
        # Fallback to recordingId if botId is missing
        bot_id = payload.recordingId

    try:
        meeting_id = int(bot_id.replace("bot_", ""))
    except ValueError:
        print(f"[WEBHOOK] Invalid botId/recordingId format: {bot_id}")
        raise HTTPException(status_code=400, detail="Invalid botId/recordingId")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        print(f"[WEBHOOK] Meeting not found: {meeting_id}")
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not payload.blobUrl:
        print(f"[WEBHOOK] No blobUrl provided for meeting {meeting_id}")
        meeting.status = MeetingStatus.failed
        db.commit()
        raise HTTPException(status_code=400, detail="No blobUrl provided")

    print(f"[WEBHOOK] Downloading recording from {payload.blobUrl} for meeting {meeting_id}...")
    import requests
    try:
        # Download the file to the meeting's designated audio_file_path
        output_audio = os.path.join(UPLOAD_DIR, f"bot_meeting_{meeting.id}.webm")
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        response = requests.get(payload.blobUrl, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_audio, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        meeting.audio_file_path = output_audio
        db.commit()
        
        # Try to download speaker_events.json
        try:
            speaker_blob_url = payload.blobUrl.replace(".webm", "_speakers.json")
            speaker_response = requests.get(speaker_blob_url, stream=True, timeout=10)
            if speaker_response.status_code == 200:
                output_speakers = os.path.join(UPLOAD_DIR, f"bot_meeting_{meeting.id}_speakers.json")
                with open(output_speakers, 'wb') as f:
                    for chunk in speaker_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"[WEBHOOK] Downloaded speaker events to {output_speakers}")
        except Exception as e:
            print(f"[WEBHOOK] Could not download speaker events (optional): {e}")

        print(f"[WEBHOOK] Successfully downloaded to {output_audio}. Triggering processing...")
        celery_app.send_task("process_meeting", args=[meeting.id])
        
        return {"status": "success", "message": "File downloaded and processing triggered."}
        
    except Exception as e:
        print(f"[WEBHOOK] Failed to download file or trigger processing: {e}")
        meeting.status = MeetingStatus.failed
        db.commit()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/upload")
async def upload_meeting(
    file: UploadFile = File(...), 
    recorded_date: date = Form(default_factory=date.today),
    participants_csv: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        status=MeetingStatus.pending,
        owner_id=current_user.id
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    
    # Parse CSV if uploaded
    parse_participants_csv(db, meeting.id, participants_csv)
    
    # Trigger Celery background task
    celery_app.send_task("process_meeting", args=[meeting.id])
    
    return {"message": "Meeting uploaded successfully", "meeting_id": meeting.id}

@router.get("")
def list_meetings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meetings = (
        db.query(Meeting)
        .filter(
            or_(
                Meeting.owner_id == current_user.id,
                Meeting.participants.any(MeetingParticipant.email == current_user.email)
            )
        )
        .order_by(desc(Meeting.created_at))
        .all()
    )
    
    return [
        {
            "id": m.id,
            "title": m.title,
            "status": m.status.value,
            "created_at": m.created_at.isoformat() + "Z" if m.created_at else None
        } for m in meetings
    ]

@router.get("/{meeting_id}")
def get_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.transcript),
            joinedload(Meeting.tasks).joinedload(Task.owner),
            joinedload(Meeting.tasks).joinedload(Task.participant),
        )
        .filter(
            Meeting.id == meeting_id, 
            or_(
                Meeting.owner_id == current_user.id,
                Meeting.participants.any(MeetingParticipant.email == current_user.email)
            )
        )
        .first()
    )
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
                "owner": t.owner.name if t.owner else (t.participant.name if t.participant else "Unassigned"),
                "deadline": t.deadline,
                "status": t.status.value
            } for t in meeting.tasks
        ]

    return response

class MapSpeakerRequest(BaseModel):
    speaker_label: str
    real_name: str

@router.post("/{meeting_id}/map_speaker")
def map_speaker(meeting_id: int, request: MapSpeakerRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.owner_id == current_user.id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # UI-level mapping placeholder logic
    return {"status": "success", "message": f"Mapped {request.speaker_label} to {request.real_name}"}
