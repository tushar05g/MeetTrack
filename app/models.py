from datetime import datetime, date
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum
from pgvector.sqlalchemy import Vector

from app.database import Base

class MeetingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    extracting = "extracting"
    done = "done"
    failed = "failed"
    scheduled = "scheduled"

class TaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"

class FollowupType(str, enum.Enum):
    initial = "initial"
    reminder = "reminder"
    overdue = "overdue"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    google_calendar_token = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    voice_embedding = Column(Vector(192), nullable=True)

    tasks = relationship("Task", back_populates="owner")
    meetings = relationship("Meeting", back_populates="owner")

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    audio_file_path = Column(String)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    recorded_date = Column(Date, default=date.today)
    scheduled_time = Column(DateTime, nullable=True)
    meet_url = Column(String, nullable=True)
    bot_duration = Column(Integer, default=60)
    bot_email = Column(String, nullable=True)
    bot_password = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    transcript = relationship("Transcript", back_populates="meeting", uselist=False)
    tasks = relationship("Task", back_populates="meeting")
    participants = relationship("MeetingParticipant", back_populates="meeting")
    owner = relationship("User", back_populates="meetings")

class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    name = Column(String)
    email = Column(String)

    meeting = relationship("Meeting", back_populates="participants")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    full_text = Column(Text)
    segments = Column(JSONB)  # Store the raw array of segment dicts (start, end, text, speaker)
    embedding = Column(Vector(384), nullable=True)  # Store transcript embedding for RAG

    meeting = relationship("Meeting", back_populates="transcript")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    participant_id = Column(Integer, ForeignKey("meeting_participants.id"), nullable=True)
    description = Column(Text)
    deadline = Column(String, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending)

    meeting = relationship("Meeting", back_populates="tasks")
    owner = relationship("User", back_populates="tasks")
    participant = relationship("MeetingParticipant")
    followups = relationship("TaskFollowup", back_populates="task")

class TaskFollowup(Base):
    __tablename__ = "task_followups"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    sent_at = Column(DateTime, default=datetime.utcnow)
    type = Column(Enum(FollowupType))

    task = relationship("Task", back_populates="followups")
