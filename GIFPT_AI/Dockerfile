FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# 시스템 라이브러리 (Pillow/psycopg/mysqlclient + manim/pycairo 대비)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    libjpeg62-turbo-dev zlib1g-dev \
    libpq-dev default-libmysqlclient-dev curl \
    pkg-config libcairo2-dev libpango1.0-dev libgdk-pixbuf-2.0-0 libffi-dev \
    ffmpeg \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    dvipng \
    dvisvgm \
    ghostscript \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 복사/설치 (레이어 캐시)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# 앱 소스
COPY . /app

# 비루트 사용자
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
