"""
CAYE v3.0 — WebSocket Router
FastAPI WebSocket endpoint.
Handles connection lifecycle:
- Accept connection
- Send initial state
- Listen for client messages
- Handle disconnection
- Start Redis broadcaster on startup
"""

import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

from backend.websocket.manager import manager
from backend.websocket.broadcaster import RedisBroadcaster
from backend.websocket.handlers import ClientMessageHandler
from backend.database import get_db, SessionLocal

router = APIRouter()

# ─────────────────────────────────────────
# REDIS BROADCASTER INSTANCE
# Started as background task on app startup
# ─────────────────────────────────────────
broadcaster = RedisBroadcaster(manager)
broadcaster_task = None


# ─────────────────────────────────────────
# BROADCASTER STARTUP FUNCTION
# Called from main.py lifespan
# ─────────────────────────────────────────

async def start_broadcaster() -> None:
    """
    Starts the Redis broadcaster as a background task.
    Must be called during application startup.
    """
    global broadcaster_task

    broadcaster_task = asyncio.create_task(
        broadcaster.start()
    )

    logger.info(
        "WebSocket broadcaster started — "
        "listening on channel: caye_events"
    )


async def stop_broadcaster() -> None:
    """
    Stops the Redis broadcaster on shutdown.
    """
    global broadcaster_task

    await broadcaster.stop()

    if broadcaster_task:
        broadcaster_task.cancel()
        try:
            await broadcaster_task
        except asyncio.CancelledError:
            pass

    logger.info("WebSocket broadcaster stopped")


# ─────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ws://localhost:8000/ws
# ─────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint.
    Each connected dashboard tab = one connection.

    Connection lifecycle:
    1. Accept connection
    2. Assign unique client_id
    3. Send initial state dump
    4. Listen for client messages
    5. Handle disconnect gracefully
    """
    # Generate unique client ID
    client_id = str(uuid.uuid4())

    # Accept connection
    await manager.connect(websocket, client_id)

    # Get DB session for initial state
    db = SessionLocal()

    try:
        # Send full initial state to new client
        await manager.send_initial_state(
            client_id, db
        )

        # Create message handler
        handler = ClientMessageHandler(manager)

        # ─────────────────────────────────
        # MESSAGE LOOP
        # Listen for client messages until
        # disconnect
        # ─────────────────────────────────
        while True:
            try:
                # Wait for client message
                # (ping, state requests, etc.)
                raw_message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60s timeout
                )

                # Handle the message
                await handler.handle(
                    client_id=client_id,
                    raw_message=raw_message,
                    db_session=db
                )

            except asyncio.TimeoutError:
                # No message in 60s — send ping
                # to check if client still alive
                try:
                    await websocket.send_text(
                        '{"event":"ping",'
                        '"payload":{"timestamp":"'
                        + __import__('datetime').datetime.utcnow().isoformat()
                        + '"}}'
                    )
                except Exception:
                    # Client not responding — disconnect
                    break

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket client disconnected: "
            f"{client_id[:8]}..."
        )

    except Exception as e:
        logger.warning(
            f"WebSocket error ({client_id[:8]}...): {e}"
        )

    finally:
        # Always clean up connection
        await manager.disconnect(client_id)
        db.close()


# ─────────────────────────────────────────
# WEBSOCKET STATUS ENDPOINT
# REST endpoint to check WS stats
# ─────────────────────────────────────────

@router.get("/ws/stats")
async def websocket_stats():
    """
    Returns WebSocket connection statistics.
    Used for system health monitoring.
    """
    return {
        "websocket_status": "ONLINE",
        "active_connections": manager.active_count,
        "total_connections": manager.total_connections,
        "total_messages_sent": manager.total_messages_sent,
        "broadcaster_running": (
            broadcaster_task is not None
            and not broadcaster_task.done()
        ),
        "redis_channel": broadcaster.CHANNEL,
    }