"""
CAYE v3.0 — WebSocket Connection Manager
Manages all active client connections.
Handles connect, disconnect, and broadcast.
Thread-safe for concurrent connections.
"""

import asyncio
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from backend.websocket.events import serialize_event


class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Each connected dashboard tab = one connection.
    Broadcasts events to all connected clients.
    """

    def __init__(self):
        # Active connections: {client_id: WebSocket}
        self._connections: Dict[str, WebSocket] = {}

        # Connection metadata: {client_id: {connected_at, ...}}
        self._metadata: Dict[str, Dict] = {}

        # Thread lock for concurrent access
        self._lock = asyncio.Lock()

        # Statistics
        self._total_connections = 0
        self._total_messages_sent = 0

    # ─────────────────────────────────────
    # CONNECTION LIFECYCLE
    # ─────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str
    ) -> None:
        """
        Accepts a new WebSocket connection.
        Registers in active connections map.
        """
        await websocket.accept()

        async with self._lock:
            self._connections[client_id] = websocket
            self._metadata[client_id] = {
                "connected_at": datetime.utcnow().isoformat(),
                "messages_sent": 0,
                "client_id": client_id
            }
            self._total_connections += 1

        logger.info(
            f"WebSocket connected: {client_id} "
            f"(total active: {self.active_count})"
        )

    async def disconnect(
        self,
        client_id: str
    ) -> None:
        """
        Removes a disconnected client.
        """
        async with self._lock:
            self._connections.pop(client_id, None)
            self._metadata.pop(client_id, None)

        logger.info(
            f"WebSocket disconnected: {client_id} "
            f"(total active: {self.active_count})"
        )

    # ─────────────────────────────────────
    # SEND TO SINGLE CLIENT
    # ─────────────────────────────────────

    async def send_to_client(
        self,
        client_id: str,
        event: Dict
    ) -> bool:
        """
        Sends an event to a specific client.
        Returns True if successful.
        """
        websocket = self._connections.get(client_id)
        if not websocket:
            return False

        try:
            message = serialize_event(event)
            await websocket.send_text(message)

            # Update metadata
            if client_id in self._metadata:
                self._metadata[client_id]["messages_sent"] += 1
            self._total_messages_sent += 1

            return True

        except WebSocketDisconnect:
            await self.disconnect(client_id)
            return False

        except Exception as e:
            logger.warning(
                f"send_to_client error "
                f"({client_id}): {e}"
            )
            await self.disconnect(client_id)
            return False

    # ─────────────────────────────────────
    # BROADCAST TO ALL CLIENTS
    # ─────────────────────────────────────

    async def broadcast(
        self,
        event: Dict,
        exclude_client: Optional[str] = None
    ) -> int:
        """
        Broadcasts an event to all connected clients.
        Returns count of clients successfully reached.

        exclude_client: Skip this client_id if provided.
        """
        if not self._connections:
            return 0

        # Serialize once for all clients
        message = serialize_event(event)

        # Get snapshot of current connections
        async with self._lock:
            client_ids = list(self._connections.keys())

        # Send to all clients
        delivered = 0
        failed_clients = []

        for client_id in client_ids:
            if exclude_client and client_id == exclude_client:
                continue

            websocket = self._connections.get(client_id)
            if not websocket:
                continue

            try:
                await websocket.send_text(message)
                delivered += 1
                self._total_messages_sent += 1

                if client_id in self._metadata:
                    self._metadata[client_id]["messages_sent"] += 1

            except WebSocketDisconnect:
                failed_clients.append(client_id)

            except Exception as e:
                logger.warning(
                    f"broadcast error ({client_id}): {e}"
                )
                failed_clients.append(client_id)

        # Clean up failed connections
        for client_id in failed_clients:
            await self.disconnect(client_id)

        if delivered > 0:
            logger.debug(
                f"Broadcast: event='{event.get('event')}' "
                f"delivered={delivered} "
                f"failed={len(failed_clients)}"
            )

        return delivered

    # ─────────────────────────────────────
    # SEND INITIAL STATE TO NEW CLIENT
    # ─────────────────────────────────────

    async def send_initial_state(
        self,
        client_id: str,
        db_session
    ) -> None:
        """
        Sends current system state to newly
        connected client. Called immediately
        after connection is established.
        """
        try:
            from backend.websocket.events import (
                build_initial_state_event
            )
            from backend.models import (
                Opportunity,
                SignalState,
                ScanLog
            )
            from sqlalchemy import desc

            # Get active opportunities
            active_opps = db_session.query(
                Opportunity
            ).filter(
                Opportunity.status == "ACTIVE",
                Opportunity.market_category == "CRYPTO"
            ).order_by(
                desc(Opportunity.cis_score)
            ).limit(50).all()

            opps_list = [
                opp.to_dict() for opp in active_opps
            ]

            # Get latest signal state
            signal_state = db_session.query(
                SignalState
            ).order_by(
                desc(SignalState.created_at)
            ).first()

            signal_dict = (
                signal_state.to_dict()
                if signal_state else None
            )

            # Get latest scan log
            last_scan = db_session.query(
                ScanLog
            ).order_by(
                desc(ScanLog.scanned_at)
            ).first()

            scan_dict = (
                last_scan.to_dict()
                if last_scan else None
            )

            # Build and send initial state event
            event = build_initial_state_event(
                active_opportunities=opps_list,
                signal_state=signal_dict,
                last_scan=scan_dict,
                system_status="ONLINE"
            )

            await self.send_to_client(client_id, event)

            logger.info(
                f"Initial state sent to {client_id}: "
                f"{len(opps_list)} opportunities, "
                f"signals={'loaded' if signal_dict else 'none'}"
            )

        except Exception as e:
            logger.error(
                f"send_initial_state error "
                f"({client_id}): {e}"
            )

    # ─────────────────────────────────────
    # PROPERTIES
    # ─────────────────────────────────────

    @property
    def active_count(self) -> int:
        """Returns number of active connections."""
        return len(self._connections)

    @property
    def total_connections(self) -> int:
        """Returns total connections since startup."""
        return self._total_connections

    @property
    def total_messages_sent(self) -> int:
        """Returns total messages sent since startup."""
        return self._total_messages_sent

    def get_stats(self) -> Dict:
        """Returns connection statistics."""
        return {
            "active_connections": self.active_count,
            "total_connections": self._total_connections,
            "total_messages_sent": self._total_messages_sent,
            "clients": [
                {
                    "client_id": cid[:8] + "...",
                    "connected_at": meta.get("connected_at"),
                    "messages_sent": meta.get("messages_sent", 0)
                }
                for cid, meta in self._metadata.items()
            ]
        }


# ─────────────────────────────────────────
# GLOBAL CONNECTION MANAGER INSTANCE
# Shared across all WebSocket connections
# ─────────────────────────────────────────
manager = ConnectionManager()