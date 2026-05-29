"""
CAYE v3.0 — WebSocket Package
Real-time event broadcasting to dashboard clients.

EVENTS BROADCAST:
- initial_state:         Sent on client connect
- new_opportunity:       When opportunity passes all 4 gates
- signal_update:         When any signal state changes
- scan_complete:         After every 60s scan run
- opportunity_resolved:  When market resolves WIN/LOSS
- opportunity_expired:   When market expires unresolved

ARCHITECTURE:
- Celery tasks publish events to Redis pub/sub
- Broadcaster subscribes to Redis channel
- Manager delivers to all connected WebSocket clients
- Channel name: caye_events
"""

from backend.websocket.manager import ConnectionManager
from backend.websocket.broadcaster import RedisBroadcaster
from backend.websocket.router import router as websocket_router

__all__ = [
    "ConnectionManager",
    "RedisBroadcaster",
    "websocket_router",
]