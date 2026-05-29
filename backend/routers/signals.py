"""
CAYE v3.0 — Signals Router
Signal state read endpoints for dashboard.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db
from backend.models import SignalState, StablecoinSnapshot, GasSnapshot, GitHubSnapshot
from backend.schemas import SignalStateResponse, SignalSummaryResponse

router = APIRouter()


@router.get("/latest", response_model=SignalStateResponse)
async def get_latest_signal_state(db: Session = Depends(get_db)):
    """
    Returns the most recent signal state record.
    This is what the dashboard uses for all signal indicators.
    """
    state = db.query(SignalState).order_by(
        desc(SignalState.created_at)
    ).first()

    if not state:
        # Return safe defaults if no state exists
        return SignalState(
            id=0,
            stablecoin_exodus=False,
            macro_draining=False,
            insider_activity=False,
            any_abandonment=False,
            any_over_leveraged=False,
            regulatory_pressure=False,
            major_unlock_imminent=False,
            signal_data_stale=True,
            created_at=datetime.utcnow()
        )

    return state


@router.get("/summary", response_model=SignalSummaryResponse)
async def get_signal_summary(db: Session = Depends(get_db)):
    """
    Returns compact signal summary for dashboard header.
    Counts active signals and flags stale data.
    """
    state = db.query(SignalState).order_by(
        desc(SignalState.created_at)
    ).first()

    if not state:
        return {
            "created_at": datetime.utcnow(),
            "stablecoin_exodus": False,
            "macro_draining": False,
            "insider_activity": False,
            "any_abandonment": False,
            "any_over_leveraged": False,
            "regulatory_pressure": False,
            "major_unlock_imminent": False,
            "signal_data_stale": True,
            "active_signal_count": 0,
            "stablecoin_delta_48h": None,
            "weekly_delta_pct": None,
            "current_gas_gwei": None,
            "total_dockets_7d": None,
            "upcoming_unlocks": None
        }

    active_count = sum([
        state.stablecoin_exodus,
        state.macro_draining,
        state.insider_activity,
        state.any_abandonment,
        state.any_over_leveraged,
        state.regulatory_pressure,
        state.major_unlock_imminent
    ])

    return {
        "created_at": state.created_at,
        "stablecoin_exodus": state.stablecoin_exodus,
        "macro_draining": state.macro_draining,
        "insider_activity": state.insider_activity,
        "any_abandonment": state.any_abandonment,
        "any_over_leveraged": state.any_over_leveraged,
        "regulatory_pressure": state.regulatory_pressure,
        "major_unlock_imminent": state.major_unlock_imminent,
        "signal_data_stale": state.signal_data_stale,
        "active_signal_count": active_count,
        "stablecoin_delta_48h": state.stablecoin_delta_48h,
        "weekly_delta_pct": state.weekly_delta_pct,
        "current_gas_gwei": state.current_gas_gwei,
        "total_dockets_7d": state.total_dockets_7d,
        "upcoming_unlocks": state.upcoming_unlocks
    }


@router.get("/history")
async def get_signal_history(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Returns signal state history for the last N hours.
    Used for signal trend charts on dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    states = db.query(SignalState).filter(
        SignalState.created_at >= since
    ).order_by(desc(SignalState.created_at)).limit(200).all()

    return {
        "count": len(states),
        "hours": hours,
        "states": [s.to_dict() for s in states]
    }


@router.get("/stablecoin-history")
async def get_stablecoin_history(
    hours: int = Query(default=48, ge=1, le=336),
    db: Session = Depends(get_db)
):
    """
    Returns stablecoin market cap history.
    Used for stablecoin flow chart on dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    snapshots = db.query(StablecoinSnapshot).filter(
        StablecoinSnapshot.recorded_at >= since
    ).order_by(desc(StablecoinSnapshot.recorded_at)).limit(500).all()

    return {
        "count": len(snapshots),
        "hours": hours,
        "snapshots": [s.to_dict() for s in snapshots]
    }


@router.get("/gas-history")
async def get_gas_history(
    hours: int = Query(default=24, ge=1, le=72),
    db: Session = Depends(get_db)
):
    """
    Returns Ethereum gas price history.
    Used for gas anomaly chart on dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    snapshots = db.query(GasSnapshot).filter(
        GasSnapshot.recorded_at >= since
    ).order_by(desc(GasSnapshot.recorded_at)).limit(500).all()

    return {
        "count": len(snapshots),
        "hours": hours,
        "snapshots": [s.to_dict() for s in snapshots]
    }


@router.get("/github-history")
async def get_github_history(
    db: Session = Depends(get_db)
):
    """
    Returns latest GitHub commit velocity for all repos.
    Used for developer activity panel on dashboard.
    """
    from sqlalchemy import func
    from backend.config import get_settings
    settings = get_settings()

    results = []
    for repo in settings.github_repos:
        latest = db.query(GitHubSnapshot).filter(
            GitHubSnapshot.repo == repo
        ).order_by(
            desc(GitHubSnapshot.recorded_at)
        ).first()

        if latest:
            results.append(latest.to_dict())
        else:
            results.append({
                "repo": repo,
                "velocity_ratio": None,
                "abandonment_detected": False,
                "recorded_at": None
            })

    return {
        "count": len(results),
        "repos": results
    }