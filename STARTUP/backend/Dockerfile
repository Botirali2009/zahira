# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# tesseract with Uzbek Latin, Uzbek Cyrillic and Russian packs is the
# on-premise / no-cloud OCR path; libgl and libglib are Pillow's runtime deps.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-uzb \
        tesseract-ocr-uzb-cyrl \
        tesseract-ocr-rus \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-optional.txt ./
RUN pip install --no-cache-dir -r requirements-optional.txt

COPY . .

# Never run the API as root: these containers process customer tax documents.
RUN useradd --create-home --uid 10001 hujjat \
    && mkdir -p /app/var/documents \
    && chown -R hujjat:hujjat /app
USER hujjat

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
