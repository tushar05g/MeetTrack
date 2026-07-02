from app.database import SessionLocal
from app.models import User, Meeting, Task, MeetingStatus, TaskStatus
from datetime import datetime

def seed():
    db = SessionLocal()
    
    # Check if user exists
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(name="Test User", email="test@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created user: {user.name}")
    else:
        print(f"User already exists: {user.name}")

    # Create a test meeting
    meeting = Meeting(
        title="Weekly Sync",
        audio_file_path="/tmp/test.flac",
        status=MeetingStatus.done
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    print(f"Created meeting: {meeting.title}")

    # Create a test task linked to user and meeting
    task = Task(
        meeting_id=meeting.id,
        owner_id=user.id,
        description="Follow up on the API design",
        deadline="2024-11-01",
        status=TaskStatus.pending
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    print(f"Created task: {task.description} assigned to {task.owner.name}")

    db.close()
    print("Seed complete!")

if __name__ == "__main__":
    seed()
