from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum

from app.database import Base

class MeetingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    extracting = "extracting"
    done = "done"
    failed = "failed"

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
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="owner")

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    audio_file_path = Column(String)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    transcript = relationship("Transcript", back_populates="meeting", uselist=False)
    tasks = relationship("Task", back_populates="meeting")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    full_text = Column(Text)
    segments = Column(JSONB)  # Store the raw array of segment dicts (start, end, text, speaker)

    meeting = relationship("Meeting", back_populates="transcript")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(Text)
    deadline = Column(String, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending)

    meeting = relationship("Meeting", back_populates="tasks")
    owner = relationship("User", back_populates="tasks")
    followups = relationship("TaskFollowup", back_populates="task")

class TaskFollowup(Base):
    __tablename__ = "task_followups"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    sent_at = Column(DateTime, default=datetime.utcnow)
    type = Column(Enum(FollowupType))

    task = relationship("Task", back_populates="followups")
