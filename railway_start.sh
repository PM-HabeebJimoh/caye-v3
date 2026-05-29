#!/bin/bash
# CAYE v3.0 — Railway Backend Startup Script

echo "Starting CAYE v3.0 backend on Railway..."

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port ${PORT:-8000} \
  --workers 1 \
  --timeout-keep-alive 75
