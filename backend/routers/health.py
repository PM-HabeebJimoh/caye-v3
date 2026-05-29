"""
CAYE v3.0 — Health Check Router
System status and service health endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from backend.database import get_db
from backend.schemas import HealthResponse, ServiceStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Full system health check.
    Tests all critical service connections.
    """
    services = []

    # Check PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        services.append(ServiceStatus(
            name="PostgreSQL",
            status="OK",
            details="Connection healthy"
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="PostgreSQL",
            status="ERROR",
            details=str(e)
        ))

    # Check Redis
    try:
        import redis
        from backend.config import get_settings
        settings = get_settings()
        r = redis.from_url(settings.redis_url)
        r.ping()
        services.append(ServiceStatus(
            name="Redis",
            status="OK",
            details="Connection healthy"
        ))
    except Exception as e:
        services.append(ServiceStatus(
            name="Redis",
            status="ERROR",
            details=str(e)
        ))

    # Check Celery
    try:
        from backend.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.active()
        if active:
            worker_count = len(active)
            services.append(ServiceStatus(
                name="Celery",
                status="OK",
                details=f"{worker_count} worker(s) active"
            ))
        else:
            services.append(ServiceStatus(
                name="Celery",
                status="WARN",
                details="No active workers detected"
            ))
    except Exception as e:
        services.append(ServiceStatus(
            name="Celery",
            status="WARN",
            details="Worker status unavailable"
        ))

    # Determine overall status
    has_error = any(s.status == "ERROR" for s in services)
    overall_status = "DEGRADED" if has_error else "OK"

    return HealthResponse(
        status=overall_status,
        version="3.0.0",
        services=services,
        timestamp=datetime.utcnow()
    )