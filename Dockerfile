FROM python:3.11-slim

# Install system dependencies
# - xvfb is required for Playwright to run headful (headless=False)
# - ffmpeg is required for PulseAudio recording and Whisper
# - pulseaudio is required for the virtual sink
RUN apt-get update && apt-get install -y \
    xvfb \
    ffmpeg \
    pulseaudio \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install HEAVY requirements first (to cache massive AI packages like torch)
COPY requirements-heavy.txt .
RUN pip install --default-timeout=1000 --no-cache-dir --no-deps -r requirements-heavy.txt --extra-index-url https://download.pytorch.org/whl/cu121

# Install Playwright and its dependencies
RUN playwright install chromium --with-deps

# Copy and install LIGHT requirements (API, Celery, etc. - changes more often)
COPY requirements-light.txt .
RUN pip install --default-timeout=1000 --no-cache-dir --no-deps -r requirements-light.txt

# Copy the rest of the application
COPY . .

# Ensure scripts are executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PYTHONPATH=/app
ENTRYPOINT ["docker-entrypoint.sh"]
