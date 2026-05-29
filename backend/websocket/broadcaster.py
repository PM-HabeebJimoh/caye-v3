"""
CAYE v3.0 — Redis Pub/Sub Broadcaster
Subscribes to Redis caye_events channel.
Forwards all Celery task events to connected
WebSocket clients via the ConnectionManager.

FLOW:
Celery Task → Redis publish(caye_events) →
Broadcaster subscribes → Manager.broadcast()
→ All connected dashboard clients
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from loguru import logger

from backend.config import get_settings

settings = get_settings()


class RedisBroadcaster:
    """
    Subscribes to Redis pub/sub channel
    and forwards events to WebSocket clients.

    Started as background task when FastAPI
    application starts.
    """

    CHANNEL = "caye_events"
    RECONNECT_DELAY = 5  # seconds

    def __init__(self, manager):
        self.manager = manager
        self._running = False
        self._pubsub = None
        self._redis = None

    async def start(self) -> None:
        """
        Starts the Redis subscriber loop.
        Runs indefinitely in background.
        Reconnects automatically on failure.
        """
        self._running = True
        logger.info(
            f"RedisBroadcaster: starting — "
            f"channel={self.CHANNEL}"
        )

        while self._running:
            try:
                await self._subscribe_loop()
            except Exception as e:
                logger.warning(
                    f"RedisBroadcaster: connection lost — "
                    f"{e}. Reconnecting in "
                    f"{self.RECONNECT_DELAY}s..."
                )
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def stop(self) -> None:
        """
        Stops the broadcaster gracefully.
        """
        self._running = False
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(self.CHANNEL)
                await self._pubsub.close()
            except Exception:
                pass
        logger.info("RedisBroadcaster: stopped")

    async def _subscribe_loop(self) -> None:
        """
        Main subscription loop.
        Connects to Redis and listens for events.
        """
        import redis.asyncio as aioredis

        self._redis = await aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
        )

        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(self.CHANNEL)

        logger.info(
            f"RedisBroadcaster: subscribed to "
            f"channel '{self.CHANNEL}'"
        )

        async for message in self._pubsub.listen():
            if not self._running:
                break

            if message["type"] != "message":
                continue

            await self._handle_message(
                message["data"]
            )

    async def _handle_message(
        self,
        raw_data: str
    ) -> None:
        """
        Parses a Redis message and routes it
        to the correct broadcast handler.
        """
        try:
            event = json.loads(raw_data)
            event_type = event.get("event")

            if not event_type:
                return

            logger.debug(
                f"RedisBroadcaster: received "
                f"event='{event_type}'"
            )

            # Route to correct event builder
            ws_event = self._build_ws_event(event)

            if ws_event:
                delivered = await self.manager.broadcast(
                    ws_event
                )
                logger.debug(
                    f"RedisBroadcaster: broadcast "
                    f"event='{event_type}' "
                    f"to {delivered} clients"
                )

        except json.JSONDecodeError as e:
            logger.warning(
                f"RedisBroadcaster: invalid JSON: {e}"
            )
        except Exception as e:
            logger.warning(
                f"RedisBroadcaster: handle error: {e}"
            )

    def _build_ws_event(
        self,
        redis_event: dict
    ) -> Optional[dict]:
        """
        Converts a Redis pub/sub event into
        a properly formatted WebSocket event.
        """
        from backend.websocket.events import (
            build_new_opportunity_event,
            build_signal_update_event,
            build_scan_complete_event,
            build_opportunity_resolved_event,
            build_opportunity_expired_event,
        )

        event_type = redis_event.get("event")

        # ─────────────────────────────────
        # NEW OPPORTUNITY
        # ─────────────────────────────────
        if event_type == "new_opportunity":
            opportunity = redis_event.get(
                "opportunity", {}
            )
            if opportunity:
                return build_new_opportunity_event(
                    opportunity
                )

        # ─────────────────────────────────
        # SIGNAL UPDATE
        # ─────────────────────────────────
        elif event_type == "signal_update":
            signal_type = redis_event.get(
                "signal_type", "unknown"
            )
            data = redis_event.get("data", {})
            return build_signal_update_event(
                signal_type=signal_type,
                signal_state=data
            )

        # ─────────────────────────────────
        # SCAN COMPLETE
        # ─────────────────────────────────
        elif event_type == "scan_complete":
            scan_log = redis_event.get("scan_log", {})
            return build_scan_complete_event(scan_log)

        # ─────────────────────────────────
        # OPPORTUNITY RESOLVED
        # ─────────────────────────────────
        elif event_type == "opportunity_resolved":
            return build_opportunity_resolved_event(
                opportunity_id=redis_event.get(
                    "opportunity_id", 0
                ),
                status=redis_event.get(
                    "status", "UNKNOWN"
                ),
                actual_roi=redis_event.get("actual_roi"),
                resolved_at=redis_event.get(
                    "resolved_at",
                    datetime.utcnow().isoformat()
                )
            )

        # ─────────────────────────────────
        # OPPORTUNITY EXPIRED
        # ─────────────────────────────────
        elif event_type == "opportunity_expired":
            return build_opportunity_expired_event(
                opportunity_id=redis_event.get(
                    "opportunity_id", 0
                ),
                expired_at=redis_event.get(
                    "expired_at",
                    datetime.utcnow().isoformat()
                )
            )

        else:
            logger.debug(
                f"RedisBroadcaster: unknown event "
                f"type '{event_type}' — skipping"
            )
            return None