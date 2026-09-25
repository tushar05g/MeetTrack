FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# Install system dependencies
# - ffmpeg is required for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install HEAVY requirements (API, Celery, AI Models, etc.)
COPY requirements-heavy.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements-heavy.txt

# Copy the rest of the application
COPY . .

# Ensure scripts are executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PYTHONPATH=/app
ENTRYPOINT ["docker-entrypoint.sh"]
