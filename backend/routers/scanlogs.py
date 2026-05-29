"""
CAYE v3.0 — Scan Logs Router
Market scan statistics and veto log endpoints.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from backend.database import get_db
from backend.models import ScanLog, VetoLog
from backend.schemas import ScanLogResponse, ScanLogListResponse

router = APIRouter()


@router.get("/latest", response_model=ScanLogResponse)
async def get_latest_scan(
    db: Session = Depends(get_db)
):
    """
    Returns the most recent scan log entry.
    Used for the scan statistics panel on dashboard.
    """
    scan = db.query(ScanLog).order_by(
        desc(ScanLog.scanned_at)
    ).first()

    if not scan:
        return {
            "id": 0,
            "scanned_at": datetime.utcnow(),
            "markets_fetched": 0,
            "markets_crypto": 0,
            "markets_vetoed": 0,
            "opportunities_found": 0,
            "gate1_vetoed": 0,
            "gate2_vetoed": 0,
            "gate3_vetoed": 0,
            "gate4_vetoed": 0,
            "scan_duration_ms": None,
            "signal_data_stale": False,
            "error_message": None
        }

    return scan


@router.get("/history")
async def get_scan_history(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Returns scan log history for the last N hours.
    Used for scan frequency chart on dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    scans = db.query(ScanLog).filter(
        ScanLog.scanned_at >= since
    ).order_by(
        desc(ScanLog.scanned_at)
    ).limit(500).all()

    return {
        "count": len(scans),
        "hours": hours,
        "scans": [s.to_dict() for s in scans]
    }


@router.get("/vetoes")
async def get_veto_log(
    gate_number: int = Query(
        default=None,
        description="Filter by gate: 1, 2, 3, or 4"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Returns recent veto log entries.
    Used for the Veto Transparency Log panel on dashboard.
    """
    query = db.query(VetoLog)

    if gate_number:
        query = query.filter(VetoLog.gate_number == gate_number)

    total = query.count()

    vetoes = query.order_by(
        desc(VetoLog.created_at)
    ).limit(limit).all()

    return {
        "total": total,
        "vetoes": [v.to_dict() for v in vetoes]
    }


@router.get("/vetoes/summary")
async def get_veto_summary(
    db: Session = Depends(get_db)
):
    """
    Returns veto count breakdown by gate.
    Used for veto breakdown chart on dashboard.
    """
    summary = {}
    gate_names = {
        1: "Price Ceiling",
        2: "CIS Threshold",
        3: "Liquidity Minimum",
        4: "Expiry Guard"
    }

    for gate_num in [1, 2, 3, 4]:
        count = db.query(func.count(VetoLog.id)).filter(
            VetoLog.gate_number == gate_num
        ).scalar() or 0

        summary[f"gate_{gate_num}"] = {
            "gate_number": gate_num,
            "gate_name": gate_names[gate_num],
            "count": count
        }

    total = db.query(func.count(VetoLog.id)).scalar() or 0
    summary["total"] = total

    return summary