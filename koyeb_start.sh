#!/bin/bash
# CAYE v3.0 — Koyeb Backend Startup Script

echo "Starting CAYE v3.0 backend on Koyeb..."

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start FastAPI
echo "Starting FastAPI server..."
uvicorn backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --timeout-keep-alive 75
