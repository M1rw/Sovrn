# =============================================================================
# SOVRN API Dockerfile - FastAPI Backend
# =============================================================================

# -----------------------------------------------------------------------------
# Base stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Development stage
# -----------------------------------------------------------------------------
FROM base as development

# Install dev dependencies
COPY services/api/requirements.txt services/api/requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

# Copy source (will be mounted in dev)
COPY services/api/ .
COPY packages/ /packages/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# -----------------------------------------------------------------------------
# Production build stage
# -----------------------------------------------------------------------------
FROM base as builder

COPY services/api/requirements.txt .
RUN pip install --target=/install -r requirements.txt

# -----------------------------------------------------------------------------
# Production stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim as production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -s /bin/false appuser

# Copy installed packages
COPY --from=builder /install /install

# Copy application code
COPY services/api/ .

# Create artifact directory
RUN mkdir -p /var/artifacts && chown appuser:appuser /var/artifacts

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
