#!/bin/bash
source /home/tushar/miniconda3/etc/profile.d/conda.sh
conda activate meettrack

# Start Redis
redis-server --daemonize yes

# Initialize and start Postgres
initdb -D $CONDA_PREFIX/var/postgres || true
pg_ctl -D $CONDA_PREFIX/var/postgres -l $CONDA_PREFIX/var/postgres/server.log start

# Wait for DB to be up
sleep 2

# Migrations
# alembic upgrade head (Not used, tables created via SQLAlchemy directly)

# Start FastAPI and Celery in the background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
celery -A app.worker worker -B --loglevel=info --concurrency=1 &

# Wait for background jobs
wait
