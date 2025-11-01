FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl wget gnupg ca-certificates \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libwayland-client0 libxcomposite1 libxdamage1 \
    libxfixes3 libxkbcommon0 libxrandr2 xdg-utils && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# only if playwright is in requirements
RUN python -c "import importlib,sys; sys.exit(0 if importlib.util.find_spec('playwright') else 1)" \
  && playwright install chromium && playwright install-deps chromium || true
COPY . .
ENV PYTHONPATH=/app
# dev
FROM base AS dev
EXPOSE 8002
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8002","--reload"]

# prod
FROM base AS prod
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=10s --retries=5 CMD curl -fsS http://localhost:8002/health || exit 1
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8002","--workers","2"]
