import os
import sys
import json
from datetime import datetime, date
from celery import Celery
from celery.schedules import crontab

from app.database import SessionLocal
from app.models import Meeting, MeetingStatus, Transcript, Task, TaskStatus, TaskFollowup, FollowupType
from app.email_utils import send_email

# Import Phase 1 AI pipeline components
from app.services.transcribe import transcribe_audio
from app.services.diarize import diarize_audio
from app.services.extract_tasks import extract_tasks_from_transcript

celery_app = Celery(
    "meettrack",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# Configure Celery Beat to run everyday at 9:00 AM
celery_app.conf.beat_schedule = {
    'daily-overdue-check': {
        'task': 'check_overdue_tasks',
        'schedule': crontab(hour=9, minute=0),
    },
}

# Mock user mapping for testing
MOCK_USER_MAPPING = {
    "SPEAKER_00": "kirito@yopmail.com",
    "SPEAKER_01": "colleague@example.com"
}

@celery_app.task(name="process_meeting", bind=True)
def process_meeting(self, meeting_id: int):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            print(f"Meeting {meeting_id} not found.")
            return

        print(f"--- Starting Processing for Meeting {meeting.id}: {meeting.title} ---")
        meeting.status = MeetingStatus.processing
        db.commit()

        # Step 1: Transcribe
        print("[STEP 1] Transcribing audio...")
        raw_segments = transcribe_audio(meeting.audio_file_path)

        # Step 2: Diarize
        print("[STEP 2] Diarizing audio...")
        diarized_segments = diarize_audio(meeting.audio_file_path, raw_segments)
        
        full_text = "\\n".join([f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['speaker']}: {seg['text']}" for seg in diarized_segments])

        meeting.status = MeetingStatus.extracting
        db.commit()
        
        transcript = Transcript(
            meeting_id=meeting.id,
            full_text=full_text,
            segments=diarized_segments
        )
        db.add(transcript)
        db.commit()

        # Step 3: Extract Tasks
        print("[STEP 3] Extracting tasks...")
        parsed_tasks = extract_tasks_from_transcript(diarized_segments)
        
        if isinstance(parsed_tasks, dict):
            if "task" in parsed_tasks:
                parsed_tasks = parsed_tasks["task"]
            elif "actionItems" in parsed_tasks:
                parsed_tasks = parsed_tasks["actionItems"]
            else:
                # In case it wrapped it in some other key, try to find a list
                for val in parsed_tasks.values():
                    if isinstance(val, list):
                        parsed_tasks = val
                        break
        
        if not isinstance(parsed_tasks, list):
            parsed_tasks = []

        assigned_tasks_per_user = {}

        # Save Tasks to DB
        for t in parsed_tasks:
            if not isinstance(t, dict):
                continue
            owner_label = t.get("owner", "Unknown")
            new_task = Task(
                meeting_id=meeting.id,
                description=t.get("task", ""),
                deadline=t.get("deadline"),
                status=TaskStatus.pending
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            # Group for emails
            email_address = MOCK_USER_MAPPING.get(owner_label, "unknown@example.com")
            if email_address not in assigned_tasks_per_user:
                assigned_tasks_per_user[email_address] = []
            assigned_tasks_per_user[email_address].append(new_task)

        # Step 4: Send Initial Emails
        print("[STEP 4] Sending Initial Emails...")
        for email_addr, user_tasks in assigned_tasks_per_user.items():
            if email_addr == "unknown@example.com":
                continue
                
            body = f"Hello!\\n\\nYou have been assigned new action items from '{meeting.title}':\\n\\n"
            for t in user_tasks:
                body += f"- {t.description} (Due: {t.deadline or 'No deadline'})\\n"
            body += "\\nBest,\\nMeetTrack AI"

            success = send_email(email_addr, f"New Tasks from {meeting.title}", body)
            
            if success:
                for t in user_tasks:
                    followup = TaskFollowup(task_id=t.id, type=FollowupType.initial)
                    db.add(followup)
                db.commit()

        meeting.status = MeetingStatus.done
        db.commit()

        print(f"--- Processing Complete for Meeting {meeting.id} ---")

    except Exception as e:
        print(f"Error processing meeting {meeting_id}: {str(e)}")
        meeting.status = MeetingStatus.failed
        db.commit()
        raise e
    finally:
        db.close()


@celery_app.task(name="check_overdue_tasks")
def check_overdue_tasks():
    db = SessionLocal()
    try:
        print("--- Running Scheduled Task: Check Overdue Tasks ---")
        today_str = date.today().isoformat()
        
        # Simple string comparison works for YYYY-MM-DD
        overdue_tasks = db.query(Task).filter(
            Task.status != TaskStatus.done,
            Task.deadline != None,
            Task.deadline <= today_str
        ).all()
        
        print(f"Found {len(overdue_tasks)} overdue tasks.")

        # In a real app we'd group by owner_id, but here we just map by hardcoded speaker label logic
        # For simplicity in this demo, we'll just mock the sending for each overdue task.
        for t in overdue_tasks:
            # We don't have owner mapping natively connected to Task yet due to lack of User IDs,
            # so we'll just send to a generic address for demonstration
            owner_email = "kirito@yopmail.com" 
            
            subject = "OVERDUE TASK REMINDER"
            body = f"Hello,\\n\\nThis is an automated reminder that your task is overdue:\\n\\nTask: {t.description}\\nDeadline: {t.deadline}\\n\\nPlease update the status as soon as possible."
            
            success = send_email(owner_email, subject, body)
            if success:
                followup = TaskFollowup(task_id=t.id, type=FollowupType.overdue)
                db.add(followup)
                db.commit()
                
    except Exception as e:
        print(f"Error checking overdue tasks: {e}")
    finally:
        db.close()
