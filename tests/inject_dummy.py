import sys
sys.path.append('.')
from app.database import SessionLocal
from app.models import Meeting, MeetingStatus, Task, TaskStatus, TaskFollowup, FollowupType
from app.email_utils import send_email
from extract_tasks import extract_tasks_from_transcript

MOCK_USER_MAPPING = {
    "SPEAKER_00": "kirito@yopmail.com",
}

def inject_transcript_and_test():
    db = SessionLocal()
    try:
        print("--- Testing Full AI Extraction & Email Pipeline ---")
        
        # 1. Create a dummy meeting
        meeting = Meeting(
            title="Design Review Sync",
            audio_file_path="/dummy/transcript_test.mp3",
            status=MeetingStatus.processing
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        # 2. Inject a fake diarized transcript containing action items
        fake_segments = [
            {"speaker": "SPEAKER_00", "text": "Alright everyone, thanks for joining. I am assigning tasks right now.", "start": 0.0, "end": 4.0},
            {"speaker": "SPEAKER_00", "text": "SPEAKER_00, you MUST draft the new API architecture document by this Friday. This is your assigned action item.", "start": 7.5, "end": 14.0},
            {"speaker": "SPEAKER_00", "text": "SPEAKER_00, you MUST also schedule a meeting with the frontend team to review the new dashboard UI by next Tuesday. This is your second action item.", "start": 17.5, "end": 23.0},
            {"speaker": "SPEAKER_01", "text": "Understood. I will do my tasks.", "start": 23.5, "end": 28.0}
        ]
        
        print("[STEP 3] Extracting tasks via Ollama AI...")
        # 3. Ask Ollama to extract the tasks!
        parsed_tasks = extract_tasks_from_transcript(fake_segments)
        
        if isinstance(parsed_tasks, dict):
            if "task" in parsed_tasks:
                parsed_tasks = parsed_tasks["task"]
            elif "actionItems" in parsed_tasks:
                parsed_tasks = parsed_tasks["actionItems"]
            else:
                for val in parsed_tasks.values():
                    if isinstance(val, list):
                        parsed_tasks = val
                        break
                        
        if not isinstance(parsed_tasks, list):
            parsed_tasks = []
            
        print(f"\\n🧠 Ollama Extracted {len(parsed_tasks)} tasks:\\n{parsed_tasks}\\n")

        assigned_tasks_per_user = {}

        # 4. Save to DB
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

        # 5. Send Initial Emails
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
                print(f"\\n✅ SUCCESS! Email dispatched to {email_addr} with {len(user_tasks)} tasks.")
            else:
                print(f"\\n❌ FAILED to send email to {email_addr}.")

        meeting.status = MeetingStatus.done
        db.commit()

    finally:
        db.close()

if __name__ == "__main__":
    inject_transcript_and_test()
