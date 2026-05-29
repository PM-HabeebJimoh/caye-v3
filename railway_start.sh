#!/bin/bash
echo "Starting CAYE v3.0 backend on Railway..."
export PATH="$PATH:/root/.local/bin:/usr/local/bin"
echo "Running database migrations..."
python -m alembic upgrade head
echo "Starting FastAPI server..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
