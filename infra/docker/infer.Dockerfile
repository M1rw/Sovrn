# =============================================================================
# SOVRN Inference Service - Dockerfile
# =============================================================================
# Multi-stage build for llama.cpp inference service
# =============================================================================

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY services/infer/requirements.txt .

# Install Python dependencies
# Build llama-cpp-python with CPU optimizations
RUN CMAKE_ARGS="-DLLAMA_BLAS=ON -DLLAMA_BLAS_VENDOR=OpenBLAS" \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Runtime stage
# =============================================================================

FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 sovrn

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY services/infer/ .

# Create models directory
RUN mkdir -p /app/models && chown sovrn:sovrn /app/models

# Switch to app user
USER sovrn

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "main.py"]
