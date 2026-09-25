# MeetTrack: Intelligent Meeting Assistant

MeetTrack is a full-stack, AI-powered meeting assistant designed to securely transcribe audio, diarize speakers (who said what when), automatically identify speakers using Google Meet Closed Captions, extract actionable tasks, and automatically email participants.

## Key Features
1. **Live Node.js Meeting Bot**: A Dockerized headless bot (based on screenappai/meeting-bot) that joins Google Meet, automatically turns on Closed Captions, scrapes speaker names via DOM avatars, and records the meeting audio/video.
2. **Automated Scheduling**: Connect to your Google Calendar to fetch upcoming meetings, or manually schedule the bot. Celery Beat will automatically dispatch the bot via REST API.
3. **AI Transcription & Diarization**: High-speed speech-to-text using local `faster-whisper` and speaker identification using `pyannote-audio`, efficiently managed in a Celery queue to prevent GPU crashing.
4. **Global Speaker Mapping**: Mathematically maps Pyannote's acoustic voice clusters (e.g. `SPEAKER_00`) to real human names scraped from the meeting bot's Closed Caption logs!
5. **Intelligent Task Extraction**: Uses the Groq API (LLaMA-3) to read the transcript and extract action items, owners, and accurate deadlines.
6. **Robust Queue System**: A background worker queue (Celery + Redis) that orchestrates the heavy AI tasks.

## Technology Stack
- **Frontend**: React.js, Vite, Tailwind CSS (Glassmorphic modern UI)
- **Backend API**: FastAPI (Python), SQLAlchemy, PostgreSQL
- **Background Tasks**: Celery, Celery Beat, Redis
- **Live Bot**: Node.js, Puppeteer/Playwright, Docker (`screenappai` architecture)
- **AI Models**: Faster-Whisper, PyAnnote (v3.1.1), Groq API

---

## System Architecture Workflow
1. User schedules a meeting on the dashboard.
2. `Celery Beat` wakes up the `check_scheduled_meetings` task and dispatches the Node.js `meettrack-meeting-bot`.
3. The bot joins Google Meet, records the media to an `.webm` or `.mp4` file, and constantly logs active speakers into a `_speakers.json` file by monitoring the CC avatars.
4. When the meeting ends, the bot hits a webhook on FastAPI to trigger the `process_meeting` Celery task.
5. The `worker.py` pipeline converts the video to `.wav`, runs Pyannote to cluster the voices, and runs Whisper to transcribe the text.
6. The worker applies a **Global Assignment** mapping by correlating the Pyannote timestamps with the CC JSON timestamps, assigning real names to the transcript.
7. The transcript is sent to Groq for task extraction, and emails are dispatched.

---

## Running with Docker (Recommended)

This project relies heavily on Docker to orchestrate the Node.js bot alongside the Python backend.

```bash
# Build and start all services (Postgres, Redis, FastAPI, Celery Worker, Node.js Bot)
docker compose up -d --build

# Run the frontend
cd frontend
npm install
npm run dev
```

> **Note:** The worker container requires an NVIDIA GPU for AI models. Ensure `nvidia-container-toolkit` is installed on your host system. PyAnnote relies on a gated model. You MUST have a `HUGGINGFACE_TOKEN` in your `.env` that has accepted the Pyannote terms of service.
