# 多阶段构建：API + Worker + Beat 共用同一镜像
FROM python:3.12-slim AS base

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 环境变量默认值
ENV PYTHONUNBUFFERED=1
ENV USE_CELERY=true
ENV ENABLE_SCHEDULER=false

# ---- API 服务 ----
FROM base AS api
EXPOSE 8000
# workers=1：多 Worker 会导致 MQTT 客户端重复订阅和消息重复处理
# 生产环境如需多 Worker，应将 MQTT 客户端独立为单独容器
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ---- Celery Worker ----
FROM base AS worker
CMD ["celery", "-A", "app.celery_entry", "worker", "--loglevel=info", "--concurrency=4"]

# ---- Celery Beat ----
FROM base AS beat
CMD ["celery", "-A", "app.celery_entry", "beat", "--loglevel=info"]

# ---- Flower 监控 ----
FROM base AS flower
EXPOSE 5555
CMD ["celery", "-A", "app.celery_entry", "flower", "--port=5555"]
