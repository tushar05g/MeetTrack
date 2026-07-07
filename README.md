# MeetTrack: Intelligent Meeting Assistant

MeetTrack is a full-stack, AI-powered meeting assistant designed to securely transcribe audio, diarize speakers (who said what when), extract actionable tasks, and automatically email participants. It features a custom Python Playwright bot that can automatically join live Google Meet sessions and record them for you!

## Key Features
1. **Live Meeting Bot**: A Python/Playwright headless bot that joins Google Meet, waits for admission, and records the meeting audio locally using `ffmpeg` and `pulseaudio`.
2. **Automated Scheduling**: Connect to your Google Calendar to fetch upcoming meetings, or manually schedule the bot. Celery Beat will automatically dispatch the bot exactly 2 minutes before the meeting starts.
3. **AI Transcription & Diarization**: High-speed speech-to-text using local `faster-whisper` and speaker identification using `pyannote-audio`, strictly constrained to run on a 4GB VRAM GPU without crashing.
4. **Intelligent Task Extraction**: Uses the Groq API (LLaMA-3) to read the transcript and extract action items, owners, and accurate deadlines.
5. **Participant Mapping & Emails**: Upload a CSV of participants, or pull them from Google Calendar. The system automatically sends notification emails with assigned tasks.
6. **Queue System**: A robust background worker queue (Celery + Redis) that restricts processing to one heavy AI task at a time (`--concurrency=1`) to prevent GPU Out-of-Memory (OOM) errors.

## Technology Stack
- **Frontend**: React.js, Vite, Lucide Icons (Glassmorphic modern UI)
- **Backend API**: FastAPI (Python), SQLAlchemy, PostgreSQL
- **Background Tasks**: Celery, Celery Beat, Redis
- **Live Bot**: Python, Playwright, FFmpeg, PulseAudio
- **AI Models**: Faster-Whisper, PyAnnote, Groq API

---

## System Requirements
- **OS**: Linux (Ubuntu/Debian recommended for PulseAudio and ffmpeg support)
- **GPU**: NVIDIA GPU (e.g., GTX 1050 Ti) with at least 4GB VRAM
- **Dependencies**: Node.js (v18+), Conda, FFmpeg, PulseAudio (`sudo apt install ffmpeg pulseaudio`)

---

## Setup Instructions

### 1. Environment & Dependencies
Create the Conda environment and install all Python dependencies:
```bash
conda create -n meettrack python=3.11 -y
conda activate meettrack

# Install dependencies using the requirements file
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu121

# Install Playwright browsers (Required for the bot)
playwright install chromium
```

Install Frontend dependencies:
```bash
cd frontend
npm install
cd ..
```

### 2. Environment Variables (.env)
Create a `.env` file in the root directory:
```env
# Database
DATABASE_URL=postgresql://<username>@localhost/meettrack

# AI Tokens
HUGGINGFACE_TOKEN=hf_your_token_here
GROQ_API_KEY=gsk_your_token_here

# Email Configuration (for sending task notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your_email@gmail.com
EMAIL_APP_PASSWORD=your_app_password

# Google Calendar OAuth (Optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```
> **Note:** PyAnnote relies on a gated model. You MUST go to [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) and agree to their user conditions before the HuggingFace token will work.

### 3. Start Database and Redis
We run PostgreSQL and Redis directly from Conda for isolation:
```bash
conda install -c conda-forge postgresql redis -y
redis-server --daemonize yes
pg_ctl -D $CONDA_PREFIX/var/postgres -l $CONDA_PREFIX/var/postgres/server.log start
```

### 4. Database Migrations
Initialize the Postgres tables:
```bash
alembic upgrade head
```

---

## Running the Application

You will need **three** terminal windows to run the full stack:

**Terminal 1 (React Frontend):**
```bash
cd frontend
npm run dev
```

**Terminal 2 (FastAPI Server):**
```bash
conda activate meettrack
uvicorn app.main:app --reload
```

**Terminal 3 (Celery Worker + Scheduler):**
```bash
conda activate meettrack
# The -B flag is CRITICAL! It enables the Celery Beat scheduler for automated bot dispatches.
celery -A app.worker worker -B --loglevel=info --concurrency=1
```
> **Critical:** `--concurrency=1` is required to ensure only 1 audio file is processed at a time, protecting the 4GB VRAM limit.

---

## Usage
Open your browser to `http://localhost:5173`. 
- **Upload File:** Drag and drop an existing `.mp3` or `.wav` file to process it immediately.
- **Send Live Bot:** Paste a Google Meet link and schedule a time. The bot will automatically launch in the background 2 minutes before the meeting, wait for you to click "Ask to Join", and then silently record the audio!

---

## Running with Docker (Alternative)

If you prefer to run the backend and worker in Docker, you can use `docker-compose`. Ensure you have Docker and NVIDIA Container Toolkit installed (you can use `scripts/install_docker.sh` to install these dependencies on Ubuntu).

```bash
# Build and start the services (Postgres, Redis, FastAPI, Celery Worker)
docker-compose up -d --build

# The frontend still needs to be run separately
cd frontend
npm run dev
```

> **Note:** The worker container requires an NVIDIA GPU for AI models. Ensure `nvidia-container-toolkit` is installed on your host system.
