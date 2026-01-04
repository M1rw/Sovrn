# =============================================================================
# SOVRN Worker Dockerfile - Background Job Processor
# =============================================================================

# -----------------------------------------------------------------------------
# Base stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Production stage
# -----------------------------------------------------------------------------
FROM base as production

COPY services/worker/requirements.txt .
RUN pip install -r requirements.txt

COPY services/worker/ .

RUN mkdir -p /var/artifacts && \
    useradd -r -s /bin/false worker && \
    chown worker:worker /var/artifacts

USER worker

CMD ["python", "-m", "worker.main"]
