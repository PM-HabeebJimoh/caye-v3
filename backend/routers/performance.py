"""
CAYE v3.0 — Performance Router
Win rate, ROI, and statistics endpoints.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.database import get_db
from backend.models import Opportunity, HistoricalOpportunity
from backend.schemas import PerformanceSummaryResponse

router = APIRouter()


@router.get("/summary")
async def get_performance_summary(
    db: Session = Depends(get_db)
):
    """
    Returns complete performance statistics.
    Used for the Performance Tracker panel on dashboard.
    """
    # Count by status
    total = db.query(func.count(Opportunity.id)).filter(
        Opportunity.market_category == "CRYPTO"
    ).scalar() or 0

    active = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status == "ACTIVE",
        Opportunity.market_category == "CRYPTO"
    ).scalar() or 0

    won = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status == "WON",
        Opportunity.market_category == "CRYPTO"
    ).scalar() or 0

    lost = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status == "LOST",
        Opportunity.market_category == "CRYPTO"
    ).scalar() or 0

    expired = db.query(func.count(Opportunity.id)).filter(
        Opportunity.status == "EXPIRED",
        Opportunity.market_category == "CRYPTO"
    ).scalar() or 0

    # Win rate (only count resolved trades)
    resolved = won + lost
    win_rate = (won / resolved * 100) if resolved > 0 else 0.0

    # Average ROI (won trades only)
    avg_roi_result = db.query(func.avg(Opportunity.actual_roi)).filter(
        Opportunity.status == "WON",
        Opportunity.actual_roi.isnot(None),
        Opportunity.market_category == "CRYPTO"
    ).scalar()
    average_roi = float(avg_roi_result) if avg_roi_result else 0.0

    # Total P&L
    total_pnl_result = db.query(
        func.sum(Opportunity.actual_profit)
    ).filter(
        Opportunity.status.in_(["WON", "LOST"]),
        Opportunity.actual_profit.isnot(None),
        Opportunity.market_category == "CRYPTO"
    ).scalar()
    total_pnl = float(total_pnl_result) if total_pnl_result else 0.0

    # Best and worst trade ROI
    best_roi = db.query(func.max(Opportunity.actual_roi)).filter(
        Opportunity.status == "WON",
        Opportunity.market_category == "CRYPTO"
    ).scalar()

    worst_roi = db.query(func.min(Opportunity.actual_roi)).filter(
        Opportunity.status == "LOST",
        Opportunity.market_category == "CRYPTO"
    ).scalar()

    # Max drawdown (simplified: largest single loss as % of bankroll)
    max_loss = db.query(func.min(Opportunity.actual_profit)).filter(
        Opportunity.status == "LOST",
        Opportunity.actual_profit.isnot(None),
        Opportunity.market_category == "CRYPTO"
    ).scalar()
    max_drawdown = abs(float(max_loss)) if max_loss else 0.0

    # Engine breakdown
    engine_names = {
        1: "Inverse Trap",
        2: "Tail-Risk Front-Run",
        3: "Deterministic Unlock Bleed",
        4: "Macro Starvation Short"
    }
    engine_breakdown = {}
    for engine_id in [1, 2, 3, 4]:
        e_won = db.query(func.count(Opportunity.id)).filter(
            Opportunity.engine_id == engine_id,
            Opportunity.status == "WON",
            Opportunity.market_category == "CRYPTO"
        ).scalar() or 0

        e_lost = db.query(func.count(Opportunity.id)).filter(
            Opportunity.engine_id == engine_id,
            Opportunity.status == "LOST",
            Opportunity.market_category == "CRYPTO"
        ).scalar() or 0

        e_resolved = e_won + e_lost
        e_win_rate = (e_won / e_resolved * 100) if e_resolved > 0 else 0.0

        e_avg_roi = db.query(func.avg(Opportunity.actual_roi)).filter(
            Opportunity.engine_id == engine_id,
            Opportunity.status == "WON",
            Opportunity.market_category == "CRYPTO"
        ).scalar()

        engine_breakdown[f"engine_{engine_id}"] = {
            "name": engine_names[engine_id],
            "won": e_won,
            "lost": e_lost,
            "win_rate": round(e_win_rate, 1),
            "average_roi": round(float(e_avg_roi), 1) if e_avg_roi else 0.0
        }

    return {
        "total_trades": total,
        "active_trades": active,
        "won_trades": won,
        "lost_trades": lost,
        "expired_trades": expired,
        "win_rate": round(win_rate, 1),
        "average_roi": round(average_roi, 1),
        "total_profit_loss": round(total_pnl, 2),
        "max_drawdown": round(max_drawdown, 2),
        "best_trade_roi": round(float(best_roi), 1) if best_roi else None,
        "worst_trade_roi": round(float(worst_roi), 1) if worst_roi else None,
        "engine_breakdown": engine_breakdown,
    }


@router.get("/monthly")
async def get_monthly_performance(
    db: Session = Depends(get_db)
):
    """
    Returns month-by-month performance breakdown.
    Used for performance chart on dashboard.
    """
    resolved = db.query(Opportunity).filter(
        Opportunity.status.in_(["WON", "LOST"]),
        Opportunity.resolved_at.isnot(None),
        Opportunity.market_category == "CRYPTO"
    ).order_by(Opportunity.resolved_at).all()

    monthly = {}
    for opp in resolved:
        month_key = opp.resolved_at.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {
                "month": month_key,
                "won": 0,
                "lost": 0,
                "total_profit": 0.0
            }
        if opp.status == "WON":
            monthly[month_key]["won"] += 1
            monthly[month_key]["total_profit"] += (opp.actual_profit or 0)
        else:
            monthly[month_key]["lost"] += 1
            monthly[month_key]["total_profit"] += (opp.actual_profit or 0)

    return {
        "monthly": list(monthly.values())
    }