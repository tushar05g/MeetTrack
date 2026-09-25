#!/bin/bash
set -e

if [ "$1" = 'api' ]; then
    echo "Running database migrations..."
    echo "Starting FastAPI application..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
elif [ "$1" = 'worker' ]; then
    echo "Uninstalling torchvision to prevent PyTorch circular import crashes..."
    pip uninstall -y torchvision || true
    echo "Starting Celery worker..."
    exec celery -A app.worker worker -B --loglevel=info --concurrency=1
else
    exec "$@"
fi
