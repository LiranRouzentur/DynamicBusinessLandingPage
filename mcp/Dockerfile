FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/storage/workspace /app/storage/cache
VOLUME ["/app/storage"]

FROM base AS dev
EXPOSE 8003
CMD ["uvicorn","app.server:app","--host","0.0.0.0","--port","8003","--reload"]

FROM base AS prod
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD curl -fsS http://localhost:8003/health || exit 1
CMD ["uvicorn","app.server:app","--host","0.0.0.0","--port","8003","--workers","2"]
