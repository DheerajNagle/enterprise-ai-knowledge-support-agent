# ==============================================================================
# Multi-Stage Production Dockerfile for Enterprise AI Knowledge & Support Agent
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies (Compiler & Wheels)
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt README.md ./

# Compile wheels for all project and runtime dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Base Runtime Environment
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime-base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production

# Install curl for container healthcheck execution & create unprivileged user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --home-dir /home/appuser --shell /bin/bash appuser

# Install pre-built wheels from builder stage
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application source code, assets, scripts, and default database
COPY . /app

# Ensure non-root appuser owns application code and data directory
RUN chown -R appuser:appuser /app
USER appuser

# ------------------------------------------------------------------------------
# Stage 3: Target - API Service (FastAPI Gateway)
# ------------------------------------------------------------------------------
FROM runtime-base AS api

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ------------------------------------------------------------------------------
# Stage 4: Target - MCP Server Service (FastMCP SSE)
# ------------------------------------------------------------------------------
FROM runtime-base AS mcp

ENV PORT=8001
EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "scripts/run_mcp_server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8001"]

# ------------------------------------------------------------------------------
# Stage 5: Target - Streamlit Web Console
# ------------------------------------------------------------------------------
FROM runtime-base AS streamlit

ENV PORT=8501 \
    API_BASE_URL=http://api:8000
EXPOSE 8501

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
