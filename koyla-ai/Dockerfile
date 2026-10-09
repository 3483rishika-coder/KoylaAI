# Koyla AI (EvidenceOS) — single-container build for Render (also works with plain `docker run`).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    EVIDENCEOS_DATA_DIR=/data \
    HF_HUB_DISABLE_TELEMETRY=1 \
    FASTEMBED_CACHE_PATH=/opt/models/fastembed

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && pip install "psycopg[binary]" pgvector

# Bake the OCR + embedding models into the image. The cache path (FASTEMBED_CACHE_PATH) is the SAME one the app
# uses at runtime, so nothing is downloaded when the first document is uploaded.
COPY scripts/preload_models.py /tmp/preload_models.py
RUN python /tmp/preload_models.py

COPY evidenceos ./evidenceos
COPY web ./web
COPY scripts ./scripts
COPY data/manifest.json ./data/manifest.json
COPY seed ./seed

EXPOSE 10000
# Render injects $PORT (default 10000). ONE worker only: the job worker thread + SQLite live in this process.
CMD ["sh", "-c", "exec uvicorn evidenceos.api:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
