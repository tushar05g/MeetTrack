#!/bin/bash
set -e

if [ "$1" = 'api' ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Starting FastAPI application..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
elif [ "$1" = 'worker' ]; then
    echo "Starting PulseAudio daemon in background..."
    pulseaudio -D --exit-idle-time=-1
    
    echo "Starting Celery worker with Xvfb..."
    # xvfb-run -a creates a virtual screen for Playwright to draw its headful window on
    exec xvfb-run -a celery -A app.worker worker -B --loglevel=info --concurrency=1
else
    exec "$@"
fi
