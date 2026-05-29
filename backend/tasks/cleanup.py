"""
CAYE v3.0 — Task 5: cleanup_expired
Runs every 1 hour.

FLOW:
1. Find all ACTIVE opportunities past expiry date
2. For each: Query Polymarket for resolution status
3. If resolved: Determine WIN or LOSS
4. If unresolved: Mark as EXPIRED
5. Archive to historical_opportunities table
6. Update performance statistics
7. Broadcast opportunity_resolved/expired events
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)


@celery_app.task(
    name="backend.tasks.cleanup.cleanup_expired",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=3400,
    time_limit=3500,
)
def cleanup_expired(self):
    """
    Cleanup task for expired Polymarket markets.
    Runs every 1 hour.
    Resolves outcomes and archives records.
    """
    logger.info("cleanup_expired: starting")
    db = SessionLocal()

    resolved_count = 0
    expired_count = 0
    error_count = 0

    try:
        # Find all active opportunities past expiry
        expired_opps = _find_expired_opportunities(db)

        if not expired_opps:
            logger.info(
                "cleanup_expired: no expired opportunities"
            )
            return {
                "resolved": 0,
                "expired": 0,
                "errors": 0
            }

        logger.info(
            f"cleanup_expired: processing "
            f"{len(expired_opps)} expired opportunities"
        )

        for opp in expired_opps:
            try:
                outcome = asyncio.run(
                    _check_resolution(opp)
                )

                if outcome["resolved"]:
                    _mark_resolved(
                        db, opp,
                        outcome["status"],
                        outcome["resolution_price"]
                    )
                    resolved_count += 1

                    logger.info(
                        f"Resolved: {opp.question[:50]}... "
                        f"→ {outcome['status']} "
                        f"ROI={outcome.get('actual_roi', 0):.1f}%"
                    )

                else:
                    _mark_expired(db, opp)
                    expired_count += 1

                    logger.info(
                        f"Expired: {opp.question[:50]}..."
                    )

                # Archive to historical table
                _archive_opportunity(db, opp)

            except Exception as e:
                error_count += 1
                logger.warning(
                    f"cleanup_expired: error processing "
                    f"opp {opp.id}: {e}"
                )

        logger.info(
            f"cleanup_expired COMPLETE: "
            f"resolved={resolved_count} "
            f"expired={expired_count} "
            f"errors={error_count}"
        )

        return {
            "resolved": resolved_count,
            "expired": expired_count,
            "errors": error_count
        }

    except Exception as e:
        logger.error(f"cleanup_expired FAILED: {e}")
        try:
            raise self.retry(exc=e, countdown=120)
        except self.MaxRetriesExceededError:
            return {
                "resolved": resolved_count,
                "expired": expired_count,
                "errors": error_count
            }

    finally:
        db.close()


# ─────────────────────────────────────────
# HELPER: FIND EXPIRED OPPORTUNITIES
# ─────────────────────────────────────────

def _find_expired_opportunities(db) -> List:
    """
    Finds all ACTIVE opportunities past expiry date.
    """
    from backend.models import Opportunity

    now = datetime.utcnow()

    expired = db.query(Opportunity).filter(
        Opportunity.status == "ACTIVE",
        Opportunity.expiry_date <= now,
        Opportunity.market_category == "CRYPTO"
    ).all()

    return expired


# ─────────────────────────────────────────
# HELPER: CHECK RESOLUTION ON POLYMARKET
# ─────────────────────────────────────────

async def _check_resolution(opp) -> dict:
    """
    Queries Polymarket API to check if
    market has resolved and what the outcome was.

    Returns:
        resolved: bool
        status: 'WON' or 'LOST' or None
        resolution_price: float or None
        actual_roi: float or None
    """
    import httpx

    if not opp.condition_id and not opp.market_id:
        return {
            "resolved": False,
            "status": None,
            "resolution_price": None,
            "actual_roi": None
        }

    market_id = opp.condition_id or opp.market_id

    try:
        url = (
            "https://gamma-api.polymarket.com/markets"
        )
        params = {"condition_id": market_id}

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url, params=params
            )
            response.raise_for_status()
            data = response.json()

            # Handle both list and dict response
            if isinstance(data, list) and len(data) > 0:
                market_data = data[0]
            elif isinstance(data, dict):
                market_data = data
            else:
                return {
                    "resolved": False,
                    "status": None,
                    "resolution_price": None,
                    "actual_roi": None
                }

            is_resolved = market_data.get(
                "closed", False
            ) or market_data.get(
                "isResolved", False
            )

            if not is_resolved:
                return {
                    "resolved": False,
                    "status": None,
                    "resolution_price": None,
                    "actual_roi": None
                }

            # Determine winning side
            outcome_prices = market_data.get(
                "outcomePrices", []
            )

            if (isinstance(outcome_prices, list)
                    and len(outcome_prices) >= 2):
                yes_resolved = float(
                    outcome_prices[0]
                )
                no_resolved = float(
                    outcome_prices[1]
                )

                # Winning side resolves to $1.00
                if yes_resolved >= 0.99:
                    winning_side = "YES"
                    resolution_price = 1.0
                elif no_resolved >= 0.99:
                    winning_side = "NO"
                    resolution_price = 0.0
                else:
                    # Market resolved but outcome unclear
                    return {
                        "resolved": False,
                        "status": None,
                        "resolution_price": None,
                        "actual_roi": None
                    }

                # Determine WIN or LOSS
                if opp.target_side == winning_side:
                    actual_roi = (
                        1.0 / opp.entry_price - 1
                    ) * 100
                    status = "WON"
                else:
                    actual_roi = -100.0
                    status = "LOST"

                return {
                    "resolved": True,
                    "status": status,
                    "resolution_price": resolution_price,
                    "actual_roi": actual_roi
                }

    except Exception as e:
        logger.warning(
            f"_check_resolution error for "
            f"{market_id}: {e}"
        )

    return {
        "resolved": False,
        "status": None,
        "resolution_price": None,
        "actual_roi": None
    }


# ─────────────────────────────────────────
# HELPER: MARK AS RESOLVED (WON/LOST)
# ─────────────────────────────────────────

def _mark_resolved(
    db,
    opp,
    status: str,
    resolution_price: Optional[float]
) -> None:
    """
    Updates opportunity status to WON or LOST.
    Calculates actual ROI and profit/loss.
    """
    try:
        from datetime import datetime

        actual_roi = (
            (1.0 / opp.entry_price - 1) * 100
            if status == "WON"
            else -100.0
        )

        actual_profit = (
            opp.recommended_position * (
                (1.0 / opp.entry_price) - 1
            )
            if status == "WON"
            else -opp.recommended_position
        )

        opp.status = status
        opp.resolved_at = datetime.utcnow()
        opp.actual_roi = actual_roi
        opp.actual_profit = actual_profit
        opp.resolution_price = resolution_price

        db.commit()

        # Broadcast resolution event
        _broadcast_resolved(
            opp.id, status, actual_roi
        )

    except Exception as e:
        logger.error(f"_mark_resolved error: {e}")
        db.rollback()


# ─────────────────────────────────────────
# HELPER: MARK AS EXPIRED
# ─────────────────────────────────────────

def _mark_expired(db, opp) -> None:
    """
    Marks opportunity as EXPIRED when market
    ends without a detected resolution.
    """
    try:
        opp.status = "EXPIRED"
        opp.resolved_at = datetime.utcnow()
        db.commit()

        _broadcast_expired(opp.id)

    except Exception as e:
        logger.error(f"_mark_expired error: {e}")
        db.rollback()


# ─────────────────────────────────────────
# HELPER: ARCHIVE TO HISTORICAL TABLE
# ─────────────────────────────────────────

def _archive_opportunity(db, opp) -> None:
    """
    Copies resolved/expired opportunity to
    historical_opportunities table.
    """
    try:
        from backend.models import HistoricalOpportunity

        # Check if already archived
        existing = db.query(
            HistoricalOpportunity
        ).filter(
            HistoricalOpportunity.opportunity_id == opp.id
        ).first()

        if existing:
            return

        historical = HistoricalOpportunity(
            opportunity_id=opp.id,
            market_id=opp.market_id,
            question=opp.question,
            polymarket_url=opp.polymarket_url,
            engine_id=opp.engine_id,
            engine_name=opp.engine_name,
            entry_price=opp.entry_price,
            target_side=opp.target_side,
            cis_score=opp.cis_score,
            recommended_position=opp.recommended_position,
            roi_pct=opp.roi_pct,
            status=opp.status,
            actual_roi=opp.actual_roi,
            actual_profit=opp.actual_profit,
            expiry_date=opp.expiry_date,
            resolved_at=opp.resolved_at,
            signal_breakdown=opp.signal_breakdown,
        )

        db.add(historical)
        db.commit()

    except Exception as e:
        logger.warning(f"_archive_opportunity error: {e}")
        db.rollback()


# ─────────────────────────────────────────
# HELPERS: BROADCAST EVENTS
# ─────────────────────────────────────────

def _broadcast_resolved(
    opportunity_id: int,
    status: str,
    actual_roi: float
) -> None:
    """
    Broadcasts opportunity_resolved event.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "opportunity_resolved",
            "opportunity_id": opportunity_id,
            "status": status,
            "actual_roi": actual_roi,
            "resolved_at": datetime.utcnow().isoformat()
        }

        r = cache._get_redis()
        if r:
            r.publish(
                "caye_events",
                json.dumps(event, default=str)
            )

    except Exception as e:
        logger.debug(f"_broadcast_resolved: {e}")


def _broadcast_expired(opportunity_id: int) -> None:
    """
    Broadcasts opportunity_expired event.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "opportunity_expired",
            "opportunity_id": opportunity_id,
            "expired_at": datetime.utcnow().isoformat()
        }

        r = cache._get_redis()
        if r:
            r.publish(
                "caye_events",
                json.dumps(event, default=str)
            )

    except Exception as e:
        logger.debug(f"_broadcast_expired: {e}")