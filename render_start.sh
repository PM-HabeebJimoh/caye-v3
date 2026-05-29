#!/bin/bash
# CAYE v3.0 — Render Backend Startup Script

echo "Starting CAYE v3.0 backend..."

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port $PORT \
  --workers 1 \
  --timeout-keep-alive 75
