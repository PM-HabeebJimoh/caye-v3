"""
CAYE v3.0 — Opportunities Router
All trade opportunity CRUD and filter endpoints.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.database import get_db
from backend.models import Opportunity, HistoricalOpportunity
from backend.schemas import (
    OpportunityResponse,
    OpportunityListResponse
)
from backend.dependencies import (
    get_pagination,
    get_opportunity_status_filter,
    get_engine_filter
)

router = APIRouter()


@router.get("/", response_model=OpportunityListResponse)
async def get_opportunities(
    status: Optional[str] = Depends(get_opportunity_status_filter),
    engine_id: Optional[int] = Depends(get_engine_filter),
    pagination: dict = Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """
    Returns list of opportunities with optional filters.
    Default returns all ACTIVE opportunities.
    Always crypto-only (enforced by DB constraint).
    """
    query = db.query(Opportunity)

    # Apply status filter
    if status:
        query = query.filter(Opportunity.status == status)
    else:
        query = query.filter(Opportunity.status == "ACTIVE")

    # Apply engine filter
    if engine_id:
        query = query.filter(Opportunity.engine_id == engine_id)

    # Always crypto only
    query = query.filter(Opportunity.market_category == "CRYPTO")

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    opportunities = query.order_by(
        desc(Opportunity.cis_score),
        desc(Opportunity.created_at)
    ).offset(
        pagination["offset"]
    ).limit(
        pagination["limit"]
    ).all()

    return OpportunityListResponse(
        total=total,
        opportunities=opportunities,
        page=pagination["page"],
        page_size=pagination["page_size"]
    )


@router.get("/active", response_model=List[OpportunityResponse])
async def get_active_opportunities(
    db: Session = Depends(get_db)
):
    """
    Returns all currently ACTIVE opportunities.
    Ordered by CIS score descending (highest conviction first).
    """
    opportunities = db.query(Opportunity).filter(
        Opportunity.status == "ACTIVE",
        Opportunity.market_category == "CRYPTO"
    ).order_by(
        desc(Opportunity.cis_score),
        desc(Opportunity.created_at)
    ).all()

    return opportunities


@router.get("/stats")
async def get_opportunity_stats(
    db: Session = Depends(get_db)
):
    """
    Returns opportunity count statistics by status and engine.
    Used for dashboard counter badges.
    """
    stats = {}

    for status in ["ACTIVE", "WON", "LOST", "EXPIRED"]:
        count = db.query(func.count(Opportunity.id)).filter(
            Opportunity.status == status,
            Opportunity.market_category == "CRYPTO"
        ).scalar() or 0
        stats[status.lower()] = count

    engine_stats = {}
    for engine_id in [1, 2, 3, 4]:
        engine_names = {
            1: "Inverse Trap",
            2: "Tail-Risk Front-Run",
            3: "Deterministic Unlock Bleed",
            4: "Macro Starvation Short"
        }
        count = db.query(func.count(Opportunity.id)).filter(
            Opportunity.engine_id == engine_id,
            Opportunity.status == "ACTIVE",
            Opportunity.market_category == "CRYPTO"
        ).scalar() or 0
        engine_stats[f"engine_{engine_id}"] = {
            "name": engine_names[engine_id],
            "active_count": count
        }

    stats["by_engine"] = engine_stats
    return stats


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns a single opportunity by ID.
    """
    opportunity = db.query(Opportunity).filter(
        Opportunity.id == opportunity_id,
        Opportunity.market_category == "CRYPTO"
    ).first()

    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail=f"Opportunity {opportunity_id} not found"
        )

    return opportunity


@router.get("/historical/list")
async def get_historical_opportunities(
    status: Optional[str] = Query(
        default=None,
        description="Filter: WON, LOST, EXPIRED"
    ),
    pagination: dict = Depends(get_pagination),
    db: Session = Depends(get_db)
):
    """
    Returns historical (resolved/expired) opportunities.
    Used for the Historical Log panel on dashboard.
    """
    query = db.query(HistoricalOpportunity)

    if status:
        query = query.filter(
            HistoricalOpportunity.status == status.upper()
        )

    total = query.count()

    records = query.order_by(
        desc(HistoricalOpportunity.archived_at)
    ).offset(
        pagination["offset"]
    ).limit(
        pagination["limit"]
    ).all()

    return {
        "total": total,
        "records": [r.to_dict() for r in records],
        "page": pagination["page"],
        "page_size": pagination["page_size"]
    }