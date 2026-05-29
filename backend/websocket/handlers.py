"""
CAYE v3.0 — WebSocket Message Handlers
Processes incoming messages from dashboard clients.
Clients can request data refreshes and send pings.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from backend.websocket.events import (
    build_pong_event,
    build_error_event,
    build_initial_state_event,
    parse_client_message,
    EventType
)


class ClientMessageHandler:
    """
    Handles messages received FROM dashboard clients.

    Supported client messages:
    - ping:              Keep-alive check
    - request_state:     Request full state refresh
    - request_signals:   Request signal state only
    - request_opps:      Request active opportunities
    - request_scan:      Request latest scan log
    """

    def __init__(self, manager):
        self.manager = manager

    async def handle(
        self,
        client_id: str,
        raw_message: str,
        db_session=None
    ) -> None:
        """
        Parses and routes an incoming client message.
        """
        message = parse_client_message(raw_message)

        if not message:
            await self.manager.send_to_client(
                client_id,
                build_error_event(
                    "Invalid message format",
                    "INVALID_JSON"
                )
            )
            return

        message_type = message.get("type", "")

        logger.debug(
            f"Client message: {client_id[:8]}... "
            f"type='{message_type}'"
        )

        # ─────────────────────────────────
        # PING → PONG
        # ─────────────────────────────────
        if message_type == EventType.PING:
            await self.manager.send_to_client(
                client_id,
                build_pong_event()
            )

        # ─────────────────────────────────
        # REQUEST FULL STATE REFRESH
        # ─────────────────────────────────
        elif message_type == "request_state":
            if db_session:
                await self.manager.send_initial_state(
                    client_id, db_session
                )
            else:
                await self.manager.send_to_client(
                    client_id,
                    build_error_event(
                        "State refresh unavailable",
                        "NO_DB_SESSION"
                    )
                )

        # ─────────────────────────────────
        # REQUEST SIGNAL STATE ONLY
        # ─────────────────────────────────
        elif message_type == "request_signals":
            await self._send_signal_state(
                client_id, db_session
            )

        # ─────────────────────────────────
        # REQUEST ACTIVE OPPORTUNITIES
        # ─────────────────────────────────
        elif message_type == "request_opportunities":
            await self._send_active_opportunities(
                client_id, db_session
            )

        # ─────────────────────────────────
        # REQUEST LATEST SCAN LOG
        # ─────────────────────────────────
        elif message_type == "request_scan":
            await self._send_latest_scan(
                client_id, db_session
            )

        # ─────────────────────────────────
        # UNKNOWN MESSAGE TYPE
        # ─────────────────────────────────
        else:
            logger.debug(
                f"Unknown message type: '{message_type}' "
                f"from {client_id[:8]}..."
            )

    async def _send_signal_state(
        self,
        client_id: str,
        db_session
    ) -> None:
        """
        Sends current signal state to requesting client.
        """
        if not db_session:
            return

        try:
            from backend.models import SignalState
            from sqlalchemy import desc
            from backend.websocket.events import (
                build_signal_update_event
            )

            state = db_session.query(
                SignalState
            ).order_by(
                desc(SignalState.created_at)
            ).first()

            if state:
                event = build_signal_update_event(
                    signal_type="refresh",
                    signal_state=state.to_dict()
                )
                await self.manager.send_to_client(
                    client_id, event
                )

        except Exception as e:
            logger.warning(
                f"_send_signal_state error: {e}"
            )

    async def _send_active_opportunities(
        self,
        client_id: str,
        db_session
    ) -> None:
        """
        Sends all active opportunities to
        requesting client.
        """
        if not db_session:
            return

        try:
            from backend.models import Opportunity
            from sqlalchemy import desc

            opps = db_session.query(
                Opportunity
            ).filter(
                Opportunity.status == "ACTIVE",
                Opportunity.market_category == "CRYPTO"
            ).order_by(
                desc(Opportunity.cis_score)
            ).limit(100).all()

            event = {
                "event": "opportunities_refresh",
                "payload": {
                    "opportunities": [
                        o.to_dict() for o in opps
                    ],
                    "count": len(opps),
                    "timestamp": (
                        datetime.utcnow().isoformat()
                    )
                }
            }

            await self.manager.send_to_client(
                client_id, event
            )

        except Exception as e:
            logger.warning(
                f"_send_active_opportunities error: {e}"
            )

    async def _send_latest_scan(
        self,
        client_id: str,
        db_session
    ) -> None:
        """
        Sends latest scan log to requesting client.
        """
        if not db_session:
            return

        try:
            from backend.models import ScanLog
            from sqlalchemy import desc
            from backend.websocket.events import (
                build_scan_complete_event
            )

            scan = db_session.query(
                ScanLog
            ).order_by(
                desc(ScanLog.scanned_at)
            ).first()

            if scan:
                event = build_scan_complete_event(
                    scan.to_dict()
                )
                await self.manager.send_to_client(
                    client_id, event
                )

        except Exception as e:
            logger.warning(
                f"_send_latest_scan error: {e}"
            )