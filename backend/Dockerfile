FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# dev target
FROM base AS dev
EXPOSE 8000
ENV ENVIRONMENT=development
CMD ["uvicorn","landing_api.main:app","--host","0.0.0.0","--port","8000","--reload"]

# prod target
FROM base AS prod
EXPOSE 8000
ENV ENVIRONMENT=production
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD curl -fsS http://localhost:8000/health || exit 1
CMD ["uvicorn","landing_api.main:app","--host","0.0.0.0","--port","8000","--workers","2"]
