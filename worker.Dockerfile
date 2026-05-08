FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxcb1 libx11-6 libxext6 libxrender1 libfontconfig1 libfreetype6 \
    libgl1 libglib2.0-0 libsm6 libice6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements-api.txt

COPY src/ ./src/
COPY data/lineamientos/ ./data/lineamientos/

RUN mkdir -p /app/data/reports /app/tmp/uploads /app/cache/enrichment

CMD ["python", "-m", "src.api.jobs.worker"]
