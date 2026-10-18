# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tzdata \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt gunicorn==22.0.0

COPY . .

RUN useradd --create-home --shell /usr/sbin/nologin yanxun \
 && mkdir -p /app/data \
 && chown -R yanxun:yanxun /app
USER yanxun

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# 采集任务状态保存在进程内存中，用 1 个 worker + 多线程，避免轮询请求落到没有任务的进程
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--timeout", "120", \
     "--access-logfile", "-", "--bind", "0.0.0.0:8000", "run:app"]
