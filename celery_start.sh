#!/bin/bash
# CAYE v3.0 — Render Celery Startup Script

echo "Starting CAYE v3.0 Celery..."

celery -A backend.celery_app worker \
  --beat \
  --loglevel=info \
  --concurrency=2 \
  --scheduler celery.beat.PersistentScheduler
