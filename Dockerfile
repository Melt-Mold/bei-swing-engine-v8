# BEI Swing Engine v8.0 — Docker image
# Multi-entry image supporting CLI, Web UI, Chat AI, and REST API.

FROM python:3.13-slim

LABEL maintainer="BEI Swing Engine"
LABEL version="8.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . .

# Ensure the package is importable
ENV PYTHONPATH=/app

# Healthcheck for API service
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: show help
CMD ["python", "run.py", "--help"]
