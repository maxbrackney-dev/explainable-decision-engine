FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal build tooling for optional C++ core build inside container
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Default to using latest artifacts dir
ENV ARTIFACTS_DIR=artifacts/latest
ENV OOD_Z_THRESHOLD=3.5
ENV EXPLAIN_TOP_K=6
ENV RATE_LIMIT_RPM=120
ENV BATCH_MAX_ROWS=250

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]