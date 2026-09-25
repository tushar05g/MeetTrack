import os
import sys
import json
import subprocess
import traceback
from datetime import datetime, date, timedelta
from celery import Celery
from celery.schedules import crontab

from app.database import SessionLocal
from app.models import Meeting, MeetingStatus, Transcript, Task, TaskStatus, TaskFollowup, FollowupType, User
from app.email_utils import send_email

# Import Phase 1 AI pipeline components
from app.services.transcribe import transcribe_audio
from app.services.diarize import diarize_audio
from app.services.extract_tasks import extract_tasks_from_transcript
from app.services.rag import extract_text_embedding, find_relevant_transcripts

celery_app = Celery(
    "meettrack",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# Configure Celery Beat to run everyday at 9:00 AM
celery_app.conf.beat_schedule = {
    'daily-overdue-check': {
        'task': 'check_overdue_tasks',
        'schedule': crontab(hour=9, minute=0),
    },
    'check-scheduled-meetings': {
        'task': 'check_scheduled_meetings',
        'schedule': 60.0,
    }
}

# Mock user mapping for testing
MOCK_USER_MAPPING = {
    "SPEAKER_00": "kirito@yopmail.com",
    "SPEAKER_01": "colleague@example.com"
}

@celery_app.task(name="run_bot_and_process")
def run_bot_and_process(meeting_id: int, meet_url: str):
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return

        print(f"[BOT DISPATCH] Dispatching screenappai/meeting-bot for {meet_url}...")
        
        import requests
        try:
            response = requests.post(
                "http://meeting-bot:3000/google/join",
                json={
                    "url": meet_url,
                    "name": "MeetTrack Bot",
                    "teamId": "meettrack",
                    "userId": str(meeting.id),
                    "bearerToken": "none",
                    "timezone": "UTC",
                    "botId": f"bot_{meeting.id}"
                },
                timeout=10
            )
            print(f"[BOT DISPATCH] API Response: {response.status_code} - {response.text}")
        except Exception as api_err:
            print(f"[BOT DISPATCH] Failed to contact meeting-bot API: {api_err}")
            meeting.status = MeetingStatus.failed
            db.commit()
            return
            
        print("[BOT] Bot dispatched successfully.")
        print("[BOT] NOTE: The bot is asynchronous. A webhook callback must be implemented in FastAPI to trigger `process_meeting` once the recording is ready and downloaded to `meeting.audio_file_path`.")
        
        meeting.status = MeetingStatus.pending # Keep pending until webhook
        db.commit()

    except Exception as e:
        print(f"Error running bot: {e}")
        traceback.print_exc()
        meeting.status = MeetingStatus.failed
        db.commit()
    finally:
        db.close()

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

        # Convert webm to wav if necessary (Pyannote crashes on webm containers)
        if meeting.audio_file_path.endswith(".webm"):
            import subprocess
            wav_path = meeting.audio_file_path.replace(".webm", ".wav")
            if not os.path.exists(wav_path):
                print(f"Converting {meeting.audio_file_path} to {wav_path} via ffmpeg...")
                subprocess.run(["ffmpeg", "-y", "-i", meeting.audio_file_path, "-ac", "1", "-ar", "16000", wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            meeting.audio_file_path = wav_path
            db.commit()

        # Delete any existing transcript from a previous run to avoid duplicates
        existing_transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
        if existing_transcript:
            db.delete(existing_transcript)
            db.commit()

        # Step 1: Transcribe (Always run Whisper to get multilingual raw text)
        print("[STEP 1] Transcribing audio...")
        raw_segments = transcribe_audio(meeting.audio_file_path)

        if not raw_segments:
            print("[STEP 1] No speech detected in audio (silent meeting). Marking as done.")
            transcript = Transcript(meeting_id=meeting.id, full_text="[No speech detected]", segments=[])
            db.add(transcript)
            meeting.status = MeetingStatus.done
            db.commit()
            return

        # Load CC data if this was a bot meeting
        output_json = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "uploads", f"bot_meeting_{meeting.id}_speakers.json")
        bot_transcript_data = None
        bot_participants = None
        
        if os.path.exists(output_json):
            try:
                with open(output_json, "r") as f:
                    data = json.load(f)
                    if data and isinstance(data, list) and isinstance(data[0], dict):
                        bot_transcript_data = data
                        bot_participants = ", ".join(list(set(d.get('name', 'Unknown') for d in data)))
            except Exception as e:
                print(f"Error loading bot JSON: {e}")

        # Step 2: Diarize (ALWAYS run Pyannote to group voices)
        print("[STEP 2] Diarizing audio using Pyannote...")
        try:
            diarized_segments = diarize_audio(meeting.audio_file_path, raw_segments)
        except Exception as diarize_err:
            print(f"[STEP 2] Diarization failed ({diarize_err}), falling back to raw transcription without speaker labels.")
            traceback.print_exc()
            diarized_segments = [
                {**seg, "speaker": seg.get("speaker", "SPEAKER_00")}
                for seg in raw_segments
            ]

        # Step 3: Tri-Factor Name Mapping
        if bot_transcript_data:
            print("[STEP 3] Live CC transcript found! Mapping Pyannote acoustic labels to CC names per-segment with fallback...")
            
            # 1. Calculate global votes to use as a fallback if a segment is missing CC
            global_speaker_votes = {}
            for d_seg in diarized_segments:
                py_speaker = d_seg.get('speaker', 'SPEAKER_00')
                d_start = d_seg.get('start', 0)
                d_end = d_seg.get('end', 0)
                
                for c_seg in bot_transcript_data:
                    # Google Meet bot outputs {"name": "User", "timestamp": 12}
                    c_time = c_seg.get('timestamp', 0)
                    
                    # If this CC timestamp falls within the audio segment
                    if d_start <= c_time <= d_end:
                        cc_speaker = c_seg.get('name', 'Unknown')
                        if py_speaker not in global_speaker_votes:
                            global_speaker_votes[py_speaker] = {}
                        global_speaker_votes[py_speaker][cc_speaker] = global_speaker_votes[py_speaker].get(cc_speaker, 0) + 1
            
            # Resolve global fallback mapping
            global_mapping = {}
            for py_spk, votes in global_speaker_votes.items():
                if votes:
                    global_mapping[py_spk] = max(votes, key=votes.get)
            
            # 2. Apply mapping globally to all segments
            for d_seg in diarized_segments:
                py_speaker = d_seg.get('speaker', 'SPEAKER_00')
                if py_speaker in global_mapping:
                    d_seg['speaker'] = global_mapping[py_speaker]

        # Normalize segments — guard against missing keys
        full_text = "\n".join([
            f"[{seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s] {seg.get('speaker', 'SPEAKER_00')}: {seg.get('text', '').strip()}"
            for seg in diarized_segments
            if seg.get('text', '').strip()  # skip empty/silent segments
        ])

        if not full_text.strip():
            print("[STEP 2] Transcript is empty after diarization (all silent segments). Marking as done.")
            transcript = Transcript(meeting_id=meeting.id, full_text="[No speech detected]", segments=diarized_segments)
            db.add(transcript)
            meeting.status = MeetingStatus.done
            db.commit()
            return

        meeting.status = MeetingStatus.extracting
        db.commit()
        
        # [RAG] Generate embedding and query past meetings
        try:
            print("[RAG] Extracting transcript text embedding...")
            transcript_embedding = extract_text_embedding(full_text)
            
            print("[RAG] Finding relevant past meetings...")
            relevant_transcripts = find_relevant_transcripts(transcript_embedding, db, meeting.id)
            rag_context_parts = []
            for rt in relevant_transcripts:
                title = rt.meeting.title if rt.meeting else "Unknown Meeting"
                rag_context_parts.append(f"Meeting: {title}\nTranscript snippet:\n{rt.full_text[:1500]}...\n")
            rag_context = "\n".join(rag_context_parts)
        except Exception as e:
            print(f"[RAG] Error in embedding/RAG: {e}")
            transcript_embedding = None
            rag_context = ""
        
        transcript = Transcript(
            meeting_id=meeting.id,
            full_text=full_text,
            segments=diarized_segments,
            embedding=transcript_embedding
        )
        db.add(transcript)
        db.commit()

        # Fetch users for context. Priority: Meeting specific (CSV/Calendar) -> Global Users
        global_users = db.query(User).all()
        lookup_users = meeting.participants if meeting.participants else global_users
        users_list = ", ".join([f"{u.name} ({u.email})" for u in lookup_users]) if lookup_users else "None configured"
        
        if bot_participants:
            users_list += f"\nLive participants scraped by bot: {bot_participants}"

        # Step 3: Extract Tasks
        print("[STEP 3] Extracting tasks...")
        meeting_date_obj = meeting.recorded_date if meeting.recorded_date else date.today()
        meeting_date_str = meeting_date_obj.strftime("%Y-%m-%d (%A)")
        
        # Pre-calculate exact calendar dates so the LLM doesn't hallucinate math
        calendar_map = []
        for i in range(14):
            d = meeting_date_obj + timedelta(days=i)
            prefix = "Today" if i == 0 else "Tomorrow" if i == 1 else "Next " + d.strftime("%A") if i >= 7 else d.strftime("%A")
            calendar_map.append(f"- {prefix}: {d.strftime('%Y-%m-%d')}")
        calendar_map_str = "\n".join(calendar_map)
        
        try:
            llm_result = extract_tasks_from_transcript(diarized_segments, meeting_date_str, users_list, calendar_map_str, rag_context)
            if isinstance(llm_result, dict):
                parsed_tasks = llm_result.get("tasks", [])
            else:
                parsed_tasks = llm_result
        except Exception as extract_err:
            print(f"[STEP 3] Task extraction failed ({extract_err}), continuing with no tasks.")
            traceback.print_exc()
            parsed_tasks = []
        
        if not isinstance(parsed_tasks, list):
            parsed_tasks = []

        assigned_tasks_per_user = {}

        # Save Tasks to DB
        for t in parsed_tasks:
            if not isinstance(t, dict):
                continue
            
            owner_label = t.get("owner", "Unknown")
            owner_email = t.get("owner_email")
            assigned_user = None
            assigned_participant = None

            # 1. Look in meeting participants first
            if owner_email:
                assigned_participant = next((p for p in meeting.participants if p.email == owner_email), None)
            if not assigned_participant:
                for p in meeting.participants:
                    if p.name and p.name.lower() in owner_label.lower():
                        assigned_participant = p
                        break
            
            # 2. Fallback to global users if not found in CSV
            if not assigned_participant:
                if owner_email:
                    assigned_user = db.query(User).filter(User.email == owner_email).first()
                if not assigned_user:
                    for u in global_users:
                        if u.name and u.name.lower() in owner_label.lower():
                            assigned_user = u
                            break

            new_task = Task(
                meeting_id=meeting.id,
                owner_id=assigned_user.id if assigned_user else None,
                participant_id=assigned_participant.id if assigned_participant else None,
                description=t.get("task", ""),
                deadline=t.get("deadline"),
                status=TaskStatus.pending
            )
            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            # Group for emails
            email_address = None
            if assigned_participant:
                email_address = assigned_participant.email
            elif assigned_user:
                email_address = assigned_user.email
            elif owner_email:
                email_address = owner_email
            else:
                email_address = "kirito@yopmail.com" # Default fallback
                
            if email_address not in assigned_tasks_per_user:
                assigned_tasks_per_user[email_address] = []
            assigned_tasks_per_user[email_address].append(new_task)

        # Step 4: Send Initial Emails
        print("[STEP 4] Sending Initial Emails...")
        for email_addr, user_tasks in assigned_tasks_per_user.items():
                
            body = f"Hello!\n\nYou have been assigned new action items from '{meeting.title}':\n\n"
            for t in user_tasks:
                body += f"- {t.description} (Due: {t.deadline or 'No deadline'})\n"
            body += "\nBest,\nMeetTrack AI"

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
        print(f"[ERROR] Failed to process meeting {meeting_id}: {e}")
        traceback.print_exc()
        
        # Mark as failed
        if 'meeting' in locals() and meeting:
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
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Simple string comparison works for YYYY-MM-DD HH:MM:SS
        overdue_tasks = db.query(Task).filter(
            Task.status != TaskStatus.done,
            Task.deadline != None,
            Task.deadline <= now_str
        ).all()
        
        print(f"Found {len(overdue_tasks)} overdue tasks.")

        # In a real app we'd group by owner_id, but here we just map by hardcoded speaker label logic
        # For simplicity in this demo, we'll just mock the sending for each overdue task.
        for t in overdue_tasks:
            if t.owner:
                owner_email = t.owner.email
            else:
                owner_email = None
                
            if not owner_email:
                print(f"[OVERDUE] Task '{t.description}' has no owner email, skipping.")
                continue
            
            subject = "OVERDUE TASK REMINDER"
            body = f"Hello,\n\nThis is an automated reminder that your task is overdue:\n\nTask: {t.description}\nDeadline: {t.deadline}\n\nPlease update the status as soon as possible."
            
            success = send_email(owner_email, subject, body)
            if success:
                followup = TaskFollowup(task_id=t.id, type=FollowupType.overdue)
                db.add(followup)
                db.commit()
                
    except Exception as e:
        print(f"Error checking overdue tasks: {e}")
    finally:
        db.close()

@celery_app.task(name="check_scheduled_meetings")
def check_scheduled_meetings():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Look for meetings scheduled within the next 2 minutes
        threshold = now + timedelta(minutes=2)
        
        upcoming_meetings = db.query(Meeting).filter(
            Meeting.status == MeetingStatus.scheduled,
            Meeting.scheduled_time <= threshold
        ).all()
        
        for meeting in upcoming_meetings:
            print(f"[SCHEDULER] Dispatching bot for meeting {meeting.id} scheduled at {meeting.scheduled_time}")
            meeting.status = MeetingStatus.pending
            db.commit()
            
            if meeting.meet_url:
                run_bot_and_process.delay(meeting.id, meeting.meet_url)
            else:
                print(f"[SCHEDULER] Error: Meeting {meeting.id} has no meet_url.")
                
    except Exception as e:
        print(f"Error in scheduler: {e}")
    finally:
        db.close()

@celery_app.task(name="process_voice_profile")
def process_voice_profile(user_id: int, file_path: str):
    print("Voice biometrics are temporarily disabled in Path B (Groq API).")
    if os.path.exists(file_path):
        os.remove(file_path)
