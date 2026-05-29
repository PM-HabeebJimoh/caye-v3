#!/bin/bash
echo "Starting CAYE v3.0..."
alembic upgrade head
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
