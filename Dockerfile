# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DOCS_DIR=/app/docs \
    HOST=0.0.0.0 \
    PORT=49721

WORKDIR /app

# Install dependencies first so this layer is cached across code edits.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY server.py .

# Bake in a copy of the docs as a fallback for running without a mounted volume.
# In docker-compose the ./docs volume mount shadows this with your live files.
COPY docs/ ./docs/

# Drop privileges: run as an unprivileged, home-less user.
# (Plain useradd, not --system, so uid 10001 doesn't trip the SYS_UID_MAX warning.)
RUN useradd --no-create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 49721

# Liveness: the port is accepting TCP connections. Reads PORT so it stays
# correct if the port is overridden at runtime.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,socket; s=socket.socket(); s.settimeout(3); s.connect(('127.0.0.1', int(os.environ.get('PORT','49721')))); s.close()" || exit 1

CMD ["python", "server.py"]
