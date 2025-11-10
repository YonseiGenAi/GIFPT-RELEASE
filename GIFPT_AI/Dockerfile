# gifpt_ai/Dockerfile
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# 시스템 라이브러리 (Pillow/psycopg/mysqlclient 대비)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    libjpeg62-turbo-dev zlib1g-dev \
    libpq-dev default-libmysqlclient-dev curl \
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

# 기본 포트 (Django)
EXPOSE 8000

# 헬스체크는 docker-compose에서 해도 됨
# CMD/ENTRYPOINT는 compose에서 command로 덮어씌우니 비워둔다.