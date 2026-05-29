"""
CAYE v3.0 — FastAPI Shared Dependencies
Reusable dependency injection for all routers.
"""

from typing import Optional
from fastapi import Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import get_settings, Settings


def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(
        default=50, ge=1, le=200,
        description="Items per page"
    )
) -> dict:
    """
    Standard pagination parameters for list endpoints.
    Returns offset and limit for DB queries.
    """
    offset = (page - 1) * page_size
    return {
        "page": page,
        "page_size": page_size,
        "offset": offset,
        "limit": page_size
    }


def get_opportunity_status_filter(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: ACTIVE, WON, LOST, EXPIRED, VETOED"
    )
) -> Optional[str]:
    """
    Validates and returns the status filter parameter.
    """
    valid_statuses = ["ACTIVE", "WON", "LOST", "EXPIRED", "VETOED"]
    if status and status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    return status.upper() if status else None


def get_engine_filter(
    engine_id: Optional[int] = Query(
        default=None,
        description="Filter by engine: 1, 2, 3, or 4"
    )
) -> Optional[int]:
    """
    Validates and returns the engine_id filter parameter.
    """
    if engine_id and engine_id not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=400,
            detail="Invalid engine_id. Must be 1, 2, 3, or 4"
        )
    return engine_id


def verify_crypto_only(db: Session = Depends(get_db)) -> bool:
    """
    Verifies the crypto-only constraint is working.
    Returns True if no non-crypto markets exist in DB.
    """
    from backend.models import Opportunity
    from sqlalchemy import func

    non_crypto_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.market_category != "CRYPTO"
    ).scalar()

    return non_crypto_count == 0