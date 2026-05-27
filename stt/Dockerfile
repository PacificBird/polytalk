# SPDX-FileCopyrightText: 2026 BizzAppDev Systems Pvt. Ltd.
# SPDX-License-Identifier: AGPL-3.0-or-later

FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

# Build-time arguments for model configuration (read from .env via Docker Compose)
ARG STT_MODEL=small
ARG STT_DEVICE=cpu
ARG STT_COMPUTE_TYPE=int8

# Export as ENV so they're available in RUN commands
ENV STT_MODEL=${STT_MODEL}
ENV STT_DEVICE=${STT_DEVICE}
ENV STT_COMPUTE_TYPE=${STT_COMPUTE_TYPE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STT_WORKERS=1

WORKDIR /app

# Install Python 3.11, pip, and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt gunicorn

COPY app /app/app

# Pre-download faster-whisper model (uses STT_MODEL env var, defaults to "small")
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('${STT_MODEL:-small}', device='${STT_DEVICE:-cpu}', compute_type='${STT_COMPUTE_TYPE:-int8}')" 2>/dev/null || \
    python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
RUN echo "Model is ${STT_MODEL}"

CMD ["sh", "-c", "gunicorn app.main:app -w ${STT_WORKERS:-1} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30"]
