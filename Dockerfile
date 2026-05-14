FROM python:3.11-slim

WORKDIR /app

# System deps (bash for eval.sh, build tools for faiss-cpu)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash build-essential && \
    rm -rf /var/lib/apt/lists/*

# Python deps first (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so first startup is instant
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

# Make eval script executable
RUN chmod +x experiments/circle_packing_demo/eval.sh

ENV PYTHONUNBUFFERED=1
ENV WANDB_DISABLED=true

EXPOSE 8000

# Railway overrides this with railway.toml startCommand
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
