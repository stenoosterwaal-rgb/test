FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by sentence-transformers / faiss
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV WANDB_DISABLED=true

# Railway sets $PORT at runtime; fallback to 8000 locally
CMD uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}
