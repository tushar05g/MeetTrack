# Requirements Document — AI Meeting Assistant (Nyota-style App)

## 1. Project Overview

**Project name:** MeetTrack (placeholder — rename as desired)

**Goal:** Build a self-hosted application that records/accepts meeting audio, transcribes it with speaker identification, automatically extracts action items with assigned owners and deadlines, emails those tasks to the relevant people, and sends automated follow-up reminders as deadlines approach or pass.

**Target environment:** Local development on a machine with an NVIDIA GTX 1050 Ti (4GB VRAM). Designed to run at zero ongoing cost using open-source/self-hosted components.

**Primary user:** Single user / small team (not built for large-scale multi-tenant production initially).

---

## 2. Functional Requirements

### 2.1 Meeting Input
- FR-1: User can upload an audio or video file (mp3, wav, mp4, m4a) of a meeting.
- FR-2: System stores the uploaded file and creates a meeting record with status tracking (`pending → transcribing → extracting → done → failed`).
- FR-3 (stretch): System can join a live Zoom/Google Meet/Teams call and record audio automatically.

### 2.2 Transcription
- FR-4: System transcribes uploaded audio into text using a speech-to-text model.
- FR-5: System identifies and labels distinct speakers in the transcript (speaker diarization).
- FR-6: System stores the full transcript (with speaker labels and timestamps) linked to the meeting record.
- FR-7: User can view the raw transcript via the application.

### 2.3 Task Extraction
- FR-8: System analyzes the diarized transcript using an LLM to identify action items, commitments, or assigned tasks mentioned during the meeting.
- FR-9: For each extracted task, system captures: task description, owner (speaker/person), deadline (if mentioned), and source meeting.
- FR-10: Extracted tasks are stored in the database with status (`open`, `in_progress`, `done`, `overdue`).
- FR-11: User can view, edit, or manually add/remove tasks per meeting.

### 2.4 Notifications & Email
- FR-12: System automatically sends an email to each task owner summarizing their assigned task(s) after a meeting is processed.
- FR-13: System runs a scheduled daily job to check for tasks nearing or past their deadline.
- FR-14: System sends automated follow-up reminder emails for tasks that are overdue or due soon.
- FR-15: Task owners can mark a task complete (via a link in the email or in-app), which stops further reminders.

### 2.5 User Management
- FR-16: System supports basic user accounts (name, email) who can be assigned as task owners.
- FR-17 (stretch): Authentication/login for multiple users to access their own meetings and tasks.

### 2.6 Dashboard / Frontend
- FR-18: User can view a list of all meetings with status and date.
- FR-19: User can view a list of all tasks across meetings, filterable by owner/status/deadline.
- FR-20: User can open a meeting to see its transcript and extracted tasks side by side.

---

## 3. Non-Functional Requirements

- NFR-1 (Cost): The system must run entirely on free/open-source components with no required paid API or subscription for core functionality.
- NFR-2 (Hardware constraint): All ML components (transcription, diarization, LLM extraction) must run within 4GB of GPU VRAM without out-of-memory failures. Models load/unload sequentially rather than concurrently.
- NFR-3 (Performance): A 30-minute meeting recording should fully process (transcription + diarization + extraction) in under 15 minutes on the target hardware.
- NFR-4 (Reliability): Failed processing jobs (e.g., corrupted audio) must be caught and marked `failed` with an error reason, not crash the worker.
- NFR-5 (Data retention): Audio files, transcripts, and tasks persist in local storage/database; no data is sent to third-party cloud services by default.
- NFR-6 (Extensibility): Architecture should allow swapping the local LLM/transcription model for a hosted API (e.g., OpenAI, Claude) later without rearchitecting the pipeline.

---

## 4. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend API | FastAPI | REST endpoints, async support |
| Background jobs | Celery + Redis | Handles transcription/extraction/email as async tasks |
| Database | PostgreSQL | Meetings, transcripts, tasks, users |
| ORM / migrations | SQLAlchemy + Alembic | |
| Transcription | faster-whisper (`small` model, int8 quantization) | Runs on local GPU |
| Diarization | WhisperX + pyannote.audio | Speaker labeling |
| LLM (task extraction) | Ollama running `llama3.2:3b` or `phi3:mini` | Local, free, quantized for 4GB VRAM |
| Email | Gmail SMTP (or SendGrid free tier) | Task notifications and reminders |
| Frontend | Jinja2 templates in FastAPI (MVP) → Next.js (later) | Keep MVP simple |
| Scheduler | Celery beat | Daily deadline-check job |

---

## 5. Data Model (Initial)

**users**
- id, name, email, created_at

**meetings**
- id, title, audio_file_path, status, uploaded_by, created_at

**transcripts**
- id, meeting_id (FK), full_text, segments (JSON: speaker, text, start_time, end_time)

**tasks**
- id, meeting_id (FK), owner_id (FK → users), description, deadline, status, created_at

**task_followups**
- id, task_id (FK), sent_at, type (`initial`, `reminder`, `overdue`)

---

## 6. Out of Scope (v1)

- Live meeting bot auto-join (Zoom/Meet/Teams) — file upload only for v1
- Multi-tenant organization/team structure
- CRM/project management tool integrations (Asana, Jira, etc.)
- Mobile app
- Real-time/live transcription during the meeting
- Advanced analytics (talk-time tracking, sentiment analysis)

---

## 7. Success Criteria (MVP Definition of Done)

1. User can upload a meeting recording and receive a diarized transcript.
2. System extracts at least 80% of clearly-stated action items (task + owner + deadline) from a test recording.
3. Task owners receive an email immediately after processing.
4. A scheduled job sends a reminder email for any task past its deadline.
5. User can view meetings, transcripts, and tasks through a basic web UI.
6. The entire pipeline runs with zero paid API usage on the developer's local machine.

---

## 8. Open Questions / Decisions Needed

- Should task "owner" be matched to a registered user account, or just stored as a free-text name extracted from the transcript?
- What's the minimum confidence threshold before a task is shown to the user vs. auto-emailed (to avoid false positives going out as emails)?
- Should reminders escalate (e.g., daily) or send once at the deadline?
