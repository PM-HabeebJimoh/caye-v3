"""
CAYE v3.0 — Task 2: update_fast_signals
Runs every 5 minutes.

Updates:
- Signal 4: Etherscan gas prices
  (MEV/insider activity detection)
- Signal 2: CoinGecko spot prices
  (Price target validation)

Both signals update the signal_state table
and broadcast via WebSocket.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from celery import shared_task
from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)


@celery_app.task(
    name="backend.tasks.fast_signals.update_fast_signals",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=240,
    time_limit=280,
)
def update_fast_signals(self):
    """
    Updates Etherscan gas + CoinGecko prices.
    Runs every 5 minutes.
    """
    logger.info("update_fast_signals: starting")
    db = SessionLocal()

    try:
        results = asyncio.run(
            _fetch_fast_signals(db)
        )

        # Update signal state in DB
        _update_signal_state(db, results)

        # Broadcast signal update
        _broadcast_signal_update(results)

        logger.info(
            f"update_fast_signals COMPLETE: "
            f"gas={results.get('current_gas_gwei')} Gwei "
            f"insider={results.get('insider_activity')} "
            f"prices_count="
            f"{len(results.get('spot_prices', {}))}"
        )

        return results

    except Exception as e:
        logger.error(f"update_fast_signals FAILED: {e}")
        try:
            raise self.retry(exc=e, countdown=30)
        except self.MaxRetriesExceededError:
            logger.error(
                "update_fast_signals: max retries exceeded"
            )
            return {}

    finally:
        db.close()


async def _fetch_fast_signals(db) -> Dict[str, Any]:
    """
    Fetches Etherscan and CoinGecko concurrently.
    """
    from backend.signals.etherscan import EtherscanSignal
    from backend.signals.coingecko import CoinGeckoSignal

    etherscan = EtherscanSignal()
    coingecko = CoinGeckoSignal()

    # Fetch concurrently
    gas_result, price_result = await asyncio.gather(
        etherscan.fetch_gas_data(db_session=db),
        coingecko.fetch_spot_prices(),
        return_exceptions=True
    )

    # Handle exceptions gracefully
    if isinstance(gas_result, Exception):
        logger.warning(f"Etherscan fetch failed: {gas_result}")
        gas_result = {
            "insider_activity": False,
            "gas_acceleration_rate": 0.0,
            "current_gas_gwei": 0,
        }

    if isinstance(price_result, Exception):
        logger.warning(f"CoinGecko fetch failed: {price_result}")
        price_result = {}

    return {
        **gas_result,
        "spot_prices": price_result,
    }


def _update_signal_state(db, results: Dict[str, Any]) -> None:
    """
    Updates the signal_state table with new fast signal data.
    Reads latest record and creates updated version.
    """
    try:
        from backend.models import SignalState
        from sqlalchemy import desc

        # Get latest state
        latest = db.query(SignalState).order_by(
            desc(SignalState.created_at)
        ).first()

        # Build new state preserving all other signals
        new_state = SignalState(
            # Preserve slow/medium signals
            stablecoin_exodus=latest.stablecoin_exodus if latest else False,
            stablecoin_delta_48h=latest.stablecoin_delta_48h if latest else None,
            total_stablecoin_mcap=latest.total_stablecoin_mcap if latest else None,
            macro_draining=latest.macro_draining if latest else False,
            weekly_delta_pct=latest.weekly_delta_pct if latest else None,
            current_net_liquidity=latest.current_net_liquidity if latest else None,
            any_abandonment=latest.any_abandonment if latest else False,
            abandonment_details=latest.abandonment_details if latest else None,
            any_over_leveraged=latest.any_over_leveraged if latest else False,
            funding_rate_details=latest.funding_rate_details if latest else None,
            regulatory_pressure=latest.regulatory_pressure if latest else False,
            total_dockets_7d=latest.total_dockets_7d if latest else None,
            major_unlock_imminent=latest.major_unlock_imminent if latest else False,
            upcoming_unlocks=latest.upcoming_unlocks if latest else None,

            # Update fast signals
            insider_activity=results.get("insider_activity", False),
            gas_acceleration_rate=results.get("gas_acceleration_rate"),
            current_gas_gwei=results.get("current_gas_gwei"),
            spot_prices=results.get("spot_prices"),

            signal_data_stale=False,
        )

        db.add(new_state)
        db.commit()

        logger.debug(
            f"signal_state updated: "
            f"insider_activity="
            f"{new_state.insider_activity}"
        )

    except Exception as e:
        logger.error(f"_update_signal_state error: {e}")
        db.rollback()


def _broadcast_signal_update(results: Dict[str, Any]) -> None:
    """
    Publishes signal_update event to Redis pub/sub.
    WebSocket manager (Phase 6) forwards to clients.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "signal_update",
            "signal_type": "fast",
            "data": {
                "insider_activity": results.get(
                    "insider_activity", False
                ),
                "current_gas_gwei": results.get(
                    "current_gas_gwei", 0
                ),
                "gas_acceleration_rate": results.get(
                    "gas_acceleration_rate", 0.0
                ),
                "spot_prices_count": len(
                    results.get("spot_prices", {})
                ),
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        r = cache._get_redis()
        if r:
            r.publish(
                "caye_events",
                json.dumps(event, default=str)
            )

    except Exception as e:
        logger.debug(f"_broadcast_signal_update: {e}")