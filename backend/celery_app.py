"""
CAYE v3.0 — Celery Application Configuration
Redis broker + result backend.
5 task queues with priority routing.
"""

from celery import Celery
from celery.utils.log import get_task_logger
from backend.config import get_settings

settings = get_settings()

# ─────────────────────────────────────────
# CREATE CELERY APP
# ─────────────────────────────────────────
celery_app = Celery(
    "caye_v3",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "backend.tasks.scan_markets",
        "backend.tasks.fast_signals",
        "backend.tasks.medium_signals",
        "backend.tasks.slow_signals",
        "backend.tasks.cleanup",
    ]
)

# ─────────────────────────────────────────
# CELERY CONFIGURATION
# ─────────────────────────────────────────
celery_app.conf.update(

    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task behavior
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Result expiry
    result_expires=3600,

    # Task time limits
    task_soft_time_limit=120,
    task_time_limit=180,

    # Retry defaults
    task_max_retries=3,
    task_default_retry_delay=60,

    # Queue routing
    task_routes={
        "backend.tasks.scan_markets.*": {
            "queue": "scan"
        },
        "backend.tasks.fast_signals.*": {
            "queue": "fast"
        },
        "backend.tasks.medium_signals.*": {
            "queue": "medium"
        },
        "backend.tasks.slow_signals.*": {
            "queue": "slow"
        },
        "backend.tasks.cleanup.*": {
            "queue": "cleanup"
        },
    },

    # Default queue
    task_default_queue="scan",

    # Worker concurrency
    worker_concurrency=4,

    # Beat schedule (loaded from beat_schedule.py)
    beat_schedule_filename="celerybeat-schedule",
)

# Load beat schedule
from backend.beat_schedule import BEAT_SCHEDULE
celery_app.conf.beat_schedule = BEAT_SCHEDULE

logger = get_task_logger(__name__)