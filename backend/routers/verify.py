"""
CAYE v3.0 — Verification Router
Crypto-only enforcement verification endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Opportunity
from backend.schemas import CryptoVerificationResponse

router = APIRouter()


@router.get("/crypto-only", response_model=CryptoVerificationResponse)
async def verify_crypto_only(db: Session = Depends(get_db)):
    """
    Verifies the 6-layer crypto-only enforcement.
    Returns count of any non-crypto markets in DB.
    Expected result: non_crypto_count = 0 always.
    """
    non_crypto_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.market_category != "CRYPTO"
    ).scalar() or 0

    total_opportunities = db.query(func.count(Opportunity.id)).scalar() or 0

    status = "ENFORCED" if non_crypto_count == 0 else "VIOLATION"

    return CryptoVerificationResponse(
        non_crypto_count=non_crypto_count,
        total_opportunities=total_opportunities,
        crypto_enforcement="6-Layer Active",
        status=status,
        timestamp=datetime.utcnow()
    )