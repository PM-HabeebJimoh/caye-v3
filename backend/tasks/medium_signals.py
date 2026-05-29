"""
CAYE v3.0 — Task 3: update_medium_signals
Runs every 30 minutes.

Updates:
- Signal 3: DefiLlama stablecoin flows
  (-$500M in 48h = stablecoin_exodus = True)
- Signal 8: Coinglass funding rates
  (>0.05% per 8h = any_over_leveraged = True)
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)


@celery_app.task(
    name="backend.tasks.medium_signals.update_medium_signals",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=1700,
    time_limit=1780,
)
def update_medium_signals(self):
    """
    Updates DefiLlama stablecoins + Coinglass funding.
    Runs every 30 minutes.
    """
    logger.info("update_medium_signals: starting")
    db = SessionLocal()

    try:
        results = asyncio.run(
            _fetch_medium_signals(db)
        )

        _update_signal_state(db, results)
        _broadcast_signal_update(results)

        logger.info(
            f"update_medium_signals COMPLETE: "
            f"stablecoin_exodus="
            f"{results.get('stablecoin_exodus')} "
            f"delta_48h="
            f"${results.get('stablecoin_delta_48h', 0)/1e9:.2f}B "
            f"over_leveraged="
            f"{results.get('any_over_leveraged')}"
        )

        return results

    except Exception as e:
        logger.error(f"update_medium_signals FAILED: {e}")
        try:
            raise self.retry(exc=e, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(
                "update_medium_signals: max retries exceeded"
            )
            return {}

    finally:
        db.close()


async def _fetch_medium_signals(db) -> Dict[str, Any]:
    """
    Fetches DefiLlama and Coinglass concurrently.
    """
    from backend.signals.defillama import DefiLlamaSignal
    from backend.signals.coinglass import CoinglassSignal

    defillama = DefiLlamaSignal()
    coinglass = CoinglassSignal()

    stable_result, funding_result = await asyncio.gather(
        defillama.fetch_stablecoin_data(db_session=db),
        coinglass.fetch_funding_data(),
        return_exceptions=True
    )

    if isinstance(stable_result, Exception):
        logger.warning(
            f"DefiLlama fetch failed: {stable_result}"
        )
        stable_result = {
            "stablecoin_exodus": False,
            "stablecoin_delta_48h": 0.0,
            "total_stablecoin_mcap": 0.0,
        }

    if isinstance(funding_result, Exception):
        logger.warning(
            f"Coinglass fetch failed: {funding_result}"
        )
        funding_result = {
            "any_over_leveraged": False,
            "funding_rate_details": {},
        }

    return {
        **stable_result,
        **funding_result,
    }


def _update_signal_state(db, results: Dict[str, Any]) -> None:
    """
    Updates signal_state with medium signal data.
    Preserves all fast and slow signal values.
    """
    try:
        from backend.models import SignalState
        from sqlalchemy import desc

        latest = db.query(SignalState).order_by(
            desc(SignalState.created_at)
        ).first()

        new_state = SignalState(
            # Update medium signals
            stablecoin_exodus=results.get(
                "stablecoin_exodus", False
            ),
            stablecoin_delta_48h=results.get(
                "stablecoin_delta_48h"
            ),
            total_stablecoin_mcap=results.get(
                "total_stablecoin_mcap"
            ),
            any_over_leveraged=results.get(
                "any_over_leveraged", False
            ),
            funding_rate_details=results.get(
                "funding_rate_details"
            ),

            # Preserve fast signals
            insider_activity=latest.insider_activity if latest else False,
            gas_acceleration_rate=latest.gas_acceleration_rate if latest else None,
            current_gas_gwei=latest.current_gas_gwei if latest else None,
            spot_prices=latest.spot_prices if latest else None,

            # Preserve slow signals
            macro_draining=latest.macro_draining if latest else False,
            weekly_delta_pct=latest.weekly_delta_pct if latest else None,
            current_net_liquidity=latest.current_net_liquidity if latest else None,
            any_abandonment=latest.any_abandonment if latest else False,
            abandonment_details=latest.abandonment_details if latest else None,
            regulatory_pressure=latest.regulatory_pressure if latest else False,
            total_dockets_7d=latest.total_dockets_7d if latest else None,
            major_unlock_imminent=latest.major_unlock_imminent if latest else False,
            upcoming_unlocks=latest.upcoming_unlocks if latest else None,

            signal_data_stale=False,
        )

        db.add(new_state)
        db.commit()

        logger.debug(
            f"signal_state updated: "
            f"stablecoin_exodus={new_state.stablecoin_exodus} "
            f"over_leveraged={new_state.any_over_leveraged}"
        )

    except Exception as e:
        logger.error(f"_update_signal_state error: {e}")
        db.rollback()


def _broadcast_signal_update(results: Dict[str, Any]) -> None:
    """
    Broadcasts medium signal update event.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "signal_update",
            "signal_type": "medium",
            "data": {
                "stablecoin_exodus": results.get(
                    "stablecoin_exodus", False
                ),
                "stablecoin_delta_48h": results.get(
                    "stablecoin_delta_48h", 0.0
                ),
                "any_over_leveraged": results.get(
                    "any_over_leveraged", False
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