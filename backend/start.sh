#!/usr/bin/env bash
# Production entrypoint for the Women Safety App backend.
#
# 1. Applies Alembic migrations (the ONLY supported schema mechanism in
#    production — Base.metadata.create_all() is never used).
# 2. Serves the FastAPI app with Gunicorn + Uvicorn workers.
#
# Binds to 0.0.0.0 and always respects the platform-provided PORT variable
# (no hardcoded production port). Used by render.yaml via `bash start.sh`.
set -euo pipefail

cd "$(dirname "$0")"

echo "[start.sh] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WEB_CONCURRENCY:-2}"

echo "[start.sh] Starting gunicorn (uvicorn workers) on ${HOST}:${PORT}..."
exec gunicorn app.main:app \
  --workers "${WORKERS}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind "${HOST}:${PORT}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --access-logfile - \
  --error-logfile -
