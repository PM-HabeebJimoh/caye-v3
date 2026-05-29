"""
CAYE v3.0 — WebSocket Event Definitions
All event types, payloads, and builders.
Every event sent to the dashboard is
defined and constructed here.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import json


# ─────────────────────────────────────────
# EVENT TYPE CONSTANTS
# ─────────────────────────────────────────

class EventType:
    INITIAL_STATE = "initial_state"
    NEW_OPPORTUNITY = "new_opportunity"
    SIGNAL_UPDATE = "signal_update"
    SCAN_COMPLETE = "scan_complete"
    OPPORTUNITY_RESOLVED = "opportunity_resolved"
    OPPORTUNITY_EXPIRED = "opportunity_expired"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


# ─────────────────────────────────────────
# EVENT BUILDER FUNCTIONS
# Each returns a JSON-serializable dict
# ─────────────────────────────────────────

def build_initial_state_event(
    active_opportunities: List[Dict],
    signal_state: Optional[Dict],
    last_scan: Optional[Dict],
    system_status: str = "ONLINE"
) -> Dict[str, Any]:
    """
    Sent immediately when a client connects.
    Gives the full current state of the system.
    """
    return {
        "event": EventType.INITIAL_STATE,
        "payload": {
            "active_opportunities": active_opportunities,
            "signal_state": signal_state,
            "last_scan": last_scan,
            "system_status": system_status,
            "scope": "Polymarket Cryptocurrency & DeFi Markets ONLY",
            "enforcement_layers": 6,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_new_opportunity_event(
    opportunity: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sent when a new opportunity passes all 4 gates.
    Dashboard adds new card to active feed.
    """
    return {
        "event": EventType.NEW_OPPORTUNITY,
        "payload": {
            "opportunity": opportunity,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_signal_update_event(
    signal_type: str,
    signal_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sent whenever any signal value changes.
    Dashboard updates signal panel indicators.

    signal_type: 'fast', 'medium', or 'slow'
    """
    return {
        "event": EventType.SIGNAL_UPDATE,
        "payload": {
            "signal_type": signal_type,
            "signal_state": signal_state,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_scan_complete_event(
    scan_log: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sent at the end of every 60s scan run.
    Dashboard updates scan statistics panel.
    """
    return {
        "event": EventType.SCAN_COMPLETE,
        "payload": {
            "scan_log": scan_log,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_opportunity_resolved_event(
    opportunity_id: int,
    status: str,
    actual_roi: Optional[float],
    resolved_at: str
) -> Dict[str, Any]:
    """
    Sent when a market resolves as WIN or LOSS.
    Dashboard moves card to Historical Log.
    """
    return {
        "event": EventType.OPPORTUNITY_RESOLVED,
        "payload": {
            "opportunity_id": opportunity_id,
            "status": status,
            "actual_roi": actual_roi,
            "resolved_at": resolved_at,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_opportunity_expired_event(
    opportunity_id: int,
    expired_at: str
) -> Dict[str, Any]:
    """
    Sent when a market expires without resolution.
    Dashboard moves card to archive.
    """
    return {
        "event": EventType.OPPORTUNITY_EXPIRED,
        "payload": {
            "opportunity_id": opportunity_id,
            "expired_at": expired_at,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_system_status_event(
    status: str,
    details: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Sent when system status changes.
    Dashboard updates status bar.
    """
    return {
        "event": EventType.SYSTEM_STATUS,
        "payload": {
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_error_event(
    message: str,
    code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sent when a system error occurs.
    Dashboard shows error notification.
    """
    return {
        "event": EventType.ERROR,
        "payload": {
            "message": message,
            "code": code,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


def build_pong_event() -> Dict[str, Any]:
    """
    Sent in response to client ping.
    Keeps connection alive.
    """
    return {
        "event": EventType.PONG,
        "payload": {
            "timestamp": datetime.utcnow().isoformat()
        }
    }


# ─────────────────────────────────────────
# EVENT SERIALIZER
# ─────────────────────────────────────────

def serialize_event(event: Dict[str, Any]) -> str:
    """
    Serializes event dict to JSON string.
    Handles datetime and float serialization.
    """
    return json.dumps(event, default=_json_serializer)


def _json_serializer(obj):
    """
    Custom JSON serializer for non-standard types.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, float):
        if obj != obj:  # NaN check
            return None
        return obj
    raise TypeError(
        f"Object of type {type(obj)} is not JSON serializable"
    )


# ─────────────────────────────────────────
# EVENT PARSER
# Parses incoming client messages
# ─────────────────────────────────────────

def parse_client_message(
    raw_message: str
) -> Optional[Dict[str, Any]]:
    """
    Parses a raw WebSocket message from client.
    Returns None if invalid JSON.
    """
    try:
        return json.loads(raw_message)
    except json.JSONDecodeError:
        return None