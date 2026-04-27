FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

COPY src/ ./src/
COPY data/lineamientos/ ./data/lineamientos/

RUN mkdir -p /app/data/reports /app/tmp/uploads /app/cache/enrichment

CMD ["python", "-m", "src.api.jobs.worker"]
