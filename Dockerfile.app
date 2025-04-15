# Use an official Python runtime as a parent image
ARG PYTHON_VERSION=3.12.2
FROM python:${PYTHON_VERSION}-slim as base

# Requiered for mount
ENV DOCKER_BUILDKIT=1

# Set non-interactive installation to avoid prompts hanging the build
ENV DEBIAN_FRONTEND=noninteractive

# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# Define environment variable for Redis
# ENV REDIS_URL=redis://redis:6379

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    build-essential \
    ffmpeg \
    gcc \
    libsndfile1-dev \
    portaudio19-dev \
    python3-pyaudio \
    weasyprint \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the current directory contents and other necessary files
COPY . .
# COPY .env.production /app/.env
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set up Python virtual environment and install dependencies using cache and bind mounts
RUN pip install --upgrade pip && \
    python3 -m venv venv

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=/app/requirements.txt \
    . venv/bin/activate && \
    pip install -r requirements.txt

# Make port 8001 available
EXPOSE 8001

# Supervisor Base Configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set Supervisor to run as the default command
CMD ["/usr/bin/supervisord"]
