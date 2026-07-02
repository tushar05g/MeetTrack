# Phased Build Plan — AI Meeting Assistant
**Stack:** FastAPI · PostgreSQL · Celery · Redis · faster-whisper · WhisperX · Ollama · Gmail SMTP
**Hardware:** NVIDIA GTX 1050 Ti (4GB VRAM)
**Budget:** $0

---

## Phase 0 — Environment Setup
**Duration:** Day 1
**Goal:** Get every tool installed and individually verified before writing any app code.

### Tasks
- [ ] Verify GPU is accessible: run `nvidia-smi` and confirm CUDA drivers are working
- [ ] Install Python 3.11+, PostgreSQL, Redis
- [ ] Install Ollama and pull the LLM model: `ollama pull llama3.2:3b`
- [ ] Install Python dependencies:
  ```
  pip install faster-whisper whisperx fastapi celery redis sqlalchemy alembic
              python-multipart uvicorn torch torchaudio pyannote.audio
  ```
- [ ] Smoke-test faster-whisper: run it on any short audio file from the command line
- [ ] Smoke-test Ollama: send a simple prompt via `ollama run llama3.2:3b` and confirm response
- [ ] Confirm Redis is running: `redis-cli ping` should return PONG

### Milestone ✅
All three components (Whisper, Ollama, Redis) respond without errors on your machine.

---

## Phase 1 — AI Pipeline as Standalone Scripts
**Duration:** Days 2–4
**Goal:** Get transcription → diarization → task extraction working end-to-end as plain Python scripts, with no web framework involved. Debugging GPU/model issues is much easier this way.

### Tasks

**Step 1 — Transcription (`transcribe.py`)**
- [ ] Accept an audio file path as input
- [ ] Load faster-whisper (`small` model, `compute_type="int8_float16"`)
- [ ] Transcribe and output raw text + word-level timestamps
- [ ] Explicitly free GPU memory after: `del model; torch.cuda.empty_cache()`
- [ ] Test on a 5–15 minute sample recording

**Step 2 — Diarization (`diarize.py`)**
- [ ] Load WhisperX alignment model + pyannote speaker diarization pipeline
- [ ] Assign speaker labels (Speaker 1, Speaker 2, ...) to each transcript segment
- [ ] Output merged segments: `[{speaker, text, start, end}, ...]`
- [ ] Test on a recording with at least 2 distinct speakers

**Step 3 — Task Extraction (`extract_tasks.py`)**
- [ ] Accept diarized transcript segments as input
- [ ] Format a prompt that instructs Ollama to return only valid JSON:
  ```
  [{"task": "...", "owner": "Speaker 1", "deadline": "YYYY-MM-DD or null"}, ...]
  ```
- [ ] Call Ollama API at `http://localhost:11434/api/generate`
- [ ] Parse and validate the JSON response
- [ ] Print extracted tasks

**Step 4 — Chain them together (`pipeline.py`)**
- [ ] Run all three steps in sequence on a single audio file
- [ ] Confirm that GPU memory is freed between steps (no OOM errors)
- [ ] Test on 3 different sample recordings to verify robustness

### Milestone ✅
Running `python pipeline.py meeting.mp3` outputs a clean list of tasks with owners and deadlines.

---

## Phase 2 — Database Schema & Models
**Duration:** Day 5
**Goal:** Design and set up the Postgres database that the application will use.

### Tasks
- [ ] Create Postgres database: `createdb meettrack`
- [ ] Set up SQLAlchemy + Alembic in a new FastAPI project folder
- [ ] Define models:

| Table | Key Columns |
|---|---|
| `users` | id, name, email, created_at |
| `meetings` | id, title, audio_file_path, status, created_at |
| `transcripts` | id, meeting_id, full_text, segments (JSONB) |
| `tasks` | id, meeting_id, owner_id, description, deadline, status |
| `task_followups` | id, task_id, sent_at, type (initial/reminder/overdue) |

- [ ] Run `alembic upgrade head` to create tables
- [ ] Write a quick seed script to insert a test user and verify relations work

### Milestone ✅
All tables exist in Postgres and SQLAlchemy models can insert/query records without errors.

---

## Phase 3 — FastAPI Backend + Celery Workers
**Duration:** Days 6–8
**Goal:** Expose the Phase 1 pipeline through an API with async background processing.

### Tasks

**API Endpoints**
- [ ] `POST /meetings/upload` — accept audio file, save to disk, create meeting row (status: `pending`), enqueue Celery task, return `meeting_id`
- [ ] `GET /meetings/{id}` — return meeting status, transcript, extracted tasks
- [ ] `GET /meetings` — list all meetings with status and date
- [ ] `GET /tasks` — list all tasks, support filter by `owner_id`, `status`, `deadline`
- [ ] `PATCH /tasks/{id}` — update task status (e.g., mark as `done`)

**Celery Pipeline Task**
- [ ] `process_meeting` Celery task that:
  1. Updates meeting status → `transcribing`
  2. Runs `transcribe.py` logic
  3. Runs `diarize.py` logic
  4. Saves transcript + segments to DB
  5. Updates meeting status → `extracting`
  6. Runs `extract_tasks.py` logic
  7. Saves extracted tasks to DB, matched to users by speaker name
  8. Updates meeting status → `done`
  9. On any exception: sets status → `failed`, logs error reason
- [ ] Run Celery with `--concurrency=1` (important — 1050 Ti cannot handle parallel GPU tasks)

**Testing**
- [ ] Upload a test file via Swagger UI (`/docs`)
- [ ] Poll `GET /meetings/{id}` and watch status change
- [ ] Confirm tasks appear in DB after processing completes

### Milestone ✅
Upload audio → background job runs → transcript and tasks are stored in DB, all via API calls.

---

## Phase 4 — Email Notifications & Follow-ups
**Duration:** Days 9–10
**Goal:** Automatically email task owners and send deadline reminders.

### Tasks

**Initial notification email**
- [ ] Set up Gmail SMTP (generate an app password in Google Account settings)
- [ ] Create `send_email(to, subject, body)` utility using Python's `smtplib`
- [ ] After Phase 3's task extraction step, send each unique task owner an email listing their assigned tasks and deadlines
- [ ] Log sent email in `task_followups` table (type: `initial`)

**Deadline reminder job**
- [ ] Add Celery beat to the project (`celery -A app beat`)
- [ ] Create a daily scheduled Celery task:
  - Query all tasks where `status != done` and `deadline <= today`
  - Send a reminder email to each owner
  - Log in `task_followups` (type: `reminder` or `overdue`)
- [ ] Handle "already reminded today" — check `task_followups` before re-sending

**Email templates**
- [ ] Initial assignment email: task name, deadline, meeting title, link to mark done
- [ ] Reminder email: task name, days overdue, meeting title, link to mark done

### Milestone ✅
Upload a meeting → tasks extracted → owners receive emails → a test task marked overdue triggers a reminder email the next day.

---

## Phase 5 — Basic Frontend (Web UI)
**Duration:** Days 11–13
**Goal:** A simple but usable web interface to view meetings and tasks.

### Tasks
- [ ] Choose approach: Jinja2 templates inside FastAPI (faster to build) or Next.js (better long-term)
  - Recommendation: Jinja2 for MVP, migrate to Next.js after core features are solid
- [ ] Pages to build:
  - **Home / Dashboard** — recent meetings, open tasks count, overdue tasks count
  - **Upload page** — file upload form, shows processing status with polling
  - **Meeting detail page** — transcript with speaker labels on the left, task list on the right
  - **Tasks page** — all tasks, filterable by owner/status/deadline, mark-complete button
- [ ] Add speaker name mapping: let user label "Speaker 1" → "Tushar", "Speaker 2" → "Rahul" after a meeting is processed, so future task emails use real names

### Milestone ✅
A non-technical person could upload a meeting, see the transcript and tasks, and mark a task complete — all through the web UI, without touching the API or DB directly.

---

## Phase 6 — Polish & Stretch Features
**Duration:** Ongoing / as desired

| Feature | Effort | Notes |
|---|---|---|
| Google Calendar OAuth — auto-detect meetings | Medium | Saves manual upload step |
| Slack notification instead of / alongside email | Low | Slack incoming webhooks, free |
| Upgrade LLM to `qwen2.5:7b` if VRAM allows | Low | Better extraction quality, test carefully |
| Switch to hosted API (OpenAI/Claude) as optional backend | Low | Just change the extraction API call |
| Live meeting bot auto-join (Zoom/Meet) | High | Recall.ai (paid) or custom Playwright bot (weeks of work) |
| Multi-user authentication (login/signup) | Medium | FastAPI OAuth2 + JWT, you already know this |
| Jira/Asana task sync after extraction | Medium | Webhooks / REST integrations |
| Talk-time analytics per speaker | Low | Already have segment durations from WhisperX |

---

## Timeline Summary

| Phase | Focus | Duration |
|---|---|---|
| 0 | Environment setup | Day 1 |
| 1 | AI pipeline scripts | Days 2–4 |
| 2 | Database schema | Day 5 |
| 3 | FastAPI + Celery | Days 6–8 |
| 4 | Email notifications | Days 9–10 |
| 5 | Web frontend | Days 11–13 |
| 6 | Polish + stretch | Ongoing |

**Estimated time to working MVP: ~2 weeks** of focused daily work (a few hours/day).

---

## Key Engineering Rules (1050 Ti specific)

1. **Never load two ML models simultaneously** — always unload Whisper before loading Ollama and vice versa.
2. **Always free GPU memory between steps:** `del model; torch.cuda.empty_cache()`
3. **Run Celery with `--concurrency=1`** — one meeting job at a time, no parallel GPU tasks.
4. **Start with short audio files (5–15 min)** while debugging; only test long meetings once each phase is stable.
5. **Use `compute_type="int8_float16"`** for faster-whisper — this is the difference between fitting in 4GB and OOM crashing.
