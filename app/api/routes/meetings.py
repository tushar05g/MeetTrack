import os
import shutil
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Meeting, MeetingStatus, Task, TaskStatus, Transcript, MeetingParticipant, User
from app.core.dependencies import get_current_user
import csv
import io
from pydantic import BaseModel
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "meettrack",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

router = APIRouter(prefix="/meetings", tags=["meetings"])

# get_db is imported from app.database

# Fixed: point to app/uploads/ relative to the project root


async def parse_participants_csv(db: AsyncSession, meeting_id: int, participants_csv: UploadFile):
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
            await db.commit()
    except Exception as e:
        print(f"Failed to parse CSV: {e}")

@router.post("/bot/join")
async def join_live_meeting(
    meet_url: str = Form(...),
    
    scheduled_time: str = Form(None),
    bot_email: str = Form(None),
    bot_password: str = Form(None),
    participants_csv: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
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
    await db.commit()
    await db.refresh(meeting)

    # Process CSV if provided
    await parse_participants_csv(db, meeting.id, participants_csv)
    
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
async def bot_webhook(payload: BotWebhookPayload, db: AsyncSession = Depends(get_db)):
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

    result = await db.execute(select(Meeting).filter(Meeting.id == meeting_id))
    meeting = result.scalars().first()
    if not meeting:
        print(f"[WEBHOOK] Meeting not found: {meeting_id}")
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not payload.blobUrl:
        print(f"[WEBHOOK] No blobUrl provided for meeting {meeting_id}")
        meeting.status = MeetingStatus.failed
        await db.commit()
        raise HTTPException(status_code=400, detail="No blobUrl provided")

    print(f"[WEBHOOK] Downloading recording from {payload.blobUrl} for meeting {meeting_id}...")
    import requests
    try:
        # Upload directly to Minio
        object_name = f"meetings/bot_meeting_{meeting.id}.webm"
        
        response = requests.get(payload.blobUrl, stream=True, timeout=60)
        response.raise_for_status()
        
        from app.core.storage import upload_fileobj_to_s3
        s3_uri = upload_fileobj_to_s3(response.raw, object_name)
                    
        meeting.audio_file_path = s3_uri
        await db.commit()
        
        # Try to download speaker_events.json and upload to Minio
        try:
            speaker_blob_url = payload.blobUrl.replace(".webm", "_speakers.json")
            speaker_response = requests.get(speaker_blob_url, stream=True, timeout=10)
            if speaker_response.status_code == 200:
                speaker_object_name = f"meetings/bot_meeting_{meeting.id}_speakers.json"
                upload_fileobj_to_s3(speaker_response.raw, speaker_object_name)
                print(f"[WEBHOOK] Downloaded speaker events to {speaker_object_name}")
        except Exception as e:
            print(f"[WEBHOOK] Could not download speaker events (optional): {e}")

        print(f"[WEBHOOK] Successfully uploaded to {s3_uri}. Triggering processing...")
        celery_app.send_task("process_meeting", args=[meeting.id])
        
        return {"status": "success", "message": "File downloaded and processing triggered."}
        
    except Exception as e:
        print(f"[WEBHOOK] Failed to download file or trigger processing: {e}")
        meeting.status = MeetingStatus.failed
        await db.commit()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/upload")
async def upload_meeting(
    file: UploadFile = File(...), 
    recorded_date: date = Form(default_factory=date.today),
    participants_csv: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Upload to Minio
    import time
    object_name = f"meetings/{int(time.time())}_{file.filename}"
    from app.core.storage import upload_fileobj_to_s3
    s3_uri = upload_fileobj_to_s3(file.file, object_name)
        
    # Create meeting record in DB
    meeting = Meeting(
        title=file.filename,
        audio_file_path=s3_uri,
        recorded_date=recorded_date,
        status=MeetingStatus.pending,
        owner_id=current_user.id
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    
    # Parse CSV if uploaded
    await parse_participants_csv(db, meeting.id, participants_csv)
    
    # Trigger Celery background task
    celery_app.send_task("process_meeting", args=[meeting.id])
    
    return {"message": "Meeting uploaded successfully", "meeting_id": meeting.id}

@router.get("")
async def list_meetings(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Meeting)
        .filter(
            or_(
                Meeting.owner_id == current_user.id,
                Meeting.participants.any(MeetingParticipant.email == current_user.email)
            )
        )
        .order_by(desc(Meeting.created_at))
    )
    meetings = result.scalars().all()
    
    return [
        {
            "id": m.id,
            "title": m.title,
            "status": m.status.value,
            "created_at": m.created_at.isoformat() + "Z" if m.created_at else None
        } for m in meetings
    ]

@router.get("/{meeting_id}")
async def get_meeting(meeting_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Meeting)
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
    )
    meeting = result.scalars().first()
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
async def map_speaker(meeting_id: int, request: MapSpeakerRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Meeting).filter(Meeting.id == meeting_id, Meeting.owner_id == current_user.id))
    meeting = result.scalars().first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # UI-level mapping placeholder logic
    return {"status": "success", "message": f"Mapped {request.speaker_label} to {request.real_name}"}
