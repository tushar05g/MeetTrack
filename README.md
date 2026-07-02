# MeetTrack: Offline Meeting AI Assistant

MeetTrack is a fully offline meeting assistant designed to securely transcribe audio, diarize speakers (who said what when), and extract actionable tasks directly on your local machine using a 4GB VRAM GPU constraint. 

## Features
1. **Transcription**: High-speed, offline speech-to-text using `faster-whisper`.
2. **Diarization**: Speaker identification using `pyannote-audio` and `whisperx`.
3. **Task Extraction**: AI-powered task extraction using a local `llama3.2:3b` model via Ollama.
4. **Queue System**: A background worker queue (Celery + Redis) that restricts processing to one meeting at a time (`--concurrency=1`) to prevent GPU Out-of-Memory (OOM) errors.
5. **Database**: PostgreSQL integration for saving meetings, transcripts, and tasks.

## System Requirements
- OS: Linux
- GPU: NVIDIA GPU (e.g., GTX 1050 Ti) with at least 4GB VRAM
- [Conda](https://docs.conda.io/en/latest/) (for managing dependencies)
- [Ollama](https://ollama.com/) (installed locally for Llama 3)

---

## Setup Instructions

### 1. Environment & Dependencies
Create the Conda environment and install all dependencies:
```bash
conda create -n meettrack python=3.11 -y
conda activate meettrack

# Install core libraries
pip install fastapi uvicorn celery python-multipart redis python-dotenv psycopg2-binary sqlalchemy alembic

# Install ML libraries (PyTorch 2.1.2 is required for older GPUs like GTX 1050 Ti)
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu121
pip install "transformers<4.38.0" "numpy<2.0.0" faster-whisper whisperx
```

### 2. Environment Variables (.env)
Create a `.env` file in the root directory:
```env
HUGGINGFACE_TOKEN=hf_your_token_here
DATABASE_URL=postgresql://<username>@localhost/meettrack
```
> **Note:** PyAnnote relies on a gated model. You MUST go to [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) and agree to their user conditions before the HuggingFace token will work.

### 3. Start Database and Redis
We run PostgreSQL and Redis directly from Conda for isolation:
```bash
# Install postgres and redis
conda install -c conda-forge postgresql redis -y

# Start Redis
redis-server --daemonize yes

# Start PostgreSQL (assuming it's already initialized via initdb)
pg_ctl -D $CONDA_PREFIX/var/postgres -l $CONDA_PREFIX/var/postgres/server.log start
```

### 4. Database Migrations
Initialize the tables:
```bash
cd app
alembic upgrade head
cd ..
```

### 5. Start the Application
You will need two terminal windows.

**Terminal 1 (FastAPI Server):**
```bash
conda activate meettrack
uvicorn app.main:app --reload
```

**Terminal 2 (Celery Worker):**
```bash
conda activate meettrack
celery -A app.worker worker --loglevel=info --concurrency=1
```
> **Critical:** `--concurrency=1` is required to ensure only 1 audio file is processed at a time, protecting the 4GB VRAM limit.

---

## API Usage

Upload a meeting audio file (`.mp3`, `.wav`, `.flac`) via the Swagger UI at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

Or via cURL:
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/meetings/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@meeting.mp3'
```
