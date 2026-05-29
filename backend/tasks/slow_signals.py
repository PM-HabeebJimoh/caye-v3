"""
CAYE v3.0 — Task 4: update_slow_signals
Runs every 6 hours.

Updates:
- Signal 5: FRED macro liquidity
  (-2% weekly = macro_draining = True)
- Signal 6: GitHub commit velocity
  (<20% ratio = any_abandonment = True)
- Signal 7: CourtListener dockets
  (>3 in 7 days = regulatory_pressure = True)
- Signal 9: Token unlock schedule
  (>$50M in 7 days = major_unlock_imminent = True)
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
    name="backend.tasks.slow_signals.update_slow_signals",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=20000,
    time_limit=21000,
)
def update_slow_signals(self):
    """
    Updates FRED + GitHub + CourtListener + TokenUnlocks.
    Runs every 6 hours.
    These signals change slowly but have high impact.
    """
    logger.info("update_slow_signals: starting")
    db = SessionLocal()

    try:
        results = asyncio.run(
            _fetch_slow_signals(db)
        )

        _update_signal_state(db, results)
        _broadcast_signal_update(results)

        logger.info(
            f"update_slow_signals COMPLETE: "
            f"macro_draining={results.get('macro_draining')} "
            f"any_abandonment={results.get('any_abandonment')} "
            f"regulatory_pressure="
            f"{results.get('regulatory_pressure')} "
            f"major_unlock_imminent="
            f"{results.get('major_unlock_imminent')}"
        )

        return results

    except Exception as e:
        logger.error(f"update_slow_signals FAILED: {e}")
        try:
            raise self.retry(exc=e, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error(
                "update_slow_signals: max retries exceeded"
            )
            return {}

    finally:
        db.close()


async def _fetch_slow_signals(db) -> Dict[str, Any]:
    """
    Fetches FRED + GitHub concurrently.
    Then fetches CourtListener (sequential — rate limits).
    Then fetches TokenUnlocks.
    """
    from backend.signals.fred import FREDSignal
    from backend.signals.github import GitHubSignal
    from backend.signals.courtlistener import CourtListenerSignal
    from backend.signals.tokenunlocks import TokenUnlocksSignal
    from backend.signals.cache import cache

    fred = FREDSignal()
    github = GitHubSignal()
    court = CourtListenerSignal()
    unlocks = TokenUnlocksSignal()

    # ─────────────────────────────────────
    # FETCH FRED + GITHUB CONCURRENTLY
    # ─────────────────────────────────────
    fred_result, github_result = await asyncio.gather(
        fred.fetch_macro_data(),
        github.fetch_commit_data(db_session=db),
        return_exceptions=True
    )

    if isinstance(fred_result, Exception):
        logger.warning(f"FRED fetch failed: {fred_result}")
        fred_result = {
            "macro_draining": False,
            "weekly_delta_pct": 0.0,
            "current_net_liquidity": 0.0,
        }

    if isinstance(github_result, Exception):
        logger.warning(
            f"GitHub fetch failed: {github_result}"
        )
        github_result = {
            "any_abandonment": False,
            "abandonment_details": {},
        }

    # ─────────────────────────────────────
    # FETCH COURTLISTENER (Sequential)
    # CourtListener has delays between requests
    # ─────────────────────────────────────
    try:
        court_result = await court.fetch_regulatory_data()
    except Exception as e:
        logger.warning(f"CourtListener fetch failed: {e}")
        court_result = {
            "regulatory_pressure": False,
            "total_dockets_7d": 0,
        }

    # ─────────────────────────────────────
    # FETCH TOKEN UNLOCKS
    # Needs spot prices for value calculation
    # ─────────────────────────────────────
    try:
        spot_prices = cache.get("coingecko_prices") or {}
        unlocks_result = await unlocks.fetch_unlock_data(
            spot_prices=spot_prices
        )
    except Exception as e:
        logger.warning(f"TokenUnlocks fetch failed: {e}")
        unlocks_result = {
            "major_unlock_imminent": False,
            "upcoming_unlocks": [],
        }

    return {
        **fred_result,
        **github_result,
        **court_result,
        **unlocks_result,
    }


def _update_signal_state(db, results: Dict[str, Any]) -> None:
    """
    Updates signal_state with all slow signal data.
    Preserves fast and medium signal values.
    """
    try:
        from backend.models import SignalState
        from sqlalchemy import desc

        latest = db.query(SignalState).order_by(
            desc(SignalState.created_at)
        ).first()

        new_state = SignalState(
            # Update slow signals
            macro_draining=results.get(
                "macro_draining", False
            ),
            weekly_delta_pct=results.get("weekly_delta_pct"),
            current_net_liquidity=results.get(
                "current_net_liquidity"
            ),
            any_abandonment=results.get(
                "any_abandonment", False
            ),
            abandonment_details=results.get(
                "abandonment_details"
            ),
            regulatory_pressure=results.get(
                "regulatory_pressure", False
            ),
            total_dockets_7d=results.get("total_dockets_7d"),
            major_unlock_imminent=results.get(
                "major_unlock_imminent", False
            ),
            upcoming_unlocks=results.get("upcoming_unlocks"),

            # Preserve fast signals
            insider_activity=latest.insider_activity if latest else False,
            gas_acceleration_rate=latest.gas_acceleration_rate if latest else None,
            current_gas_gwei=latest.current_gas_gwei if latest else None,
            spot_prices=latest.spot_prices if latest else None,

            # Preserve medium signals
            stablecoin_exodus=latest.stablecoin_exodus if latest else False,
            stablecoin_delta_48h=latest.stablecoin_delta_48h if latest else None,
            total_stablecoin_mcap=latest.total_stablecoin_mcap if latest else None,
            any_over_leveraged=latest.any_over_leveraged if latest else False,
            funding_rate_details=latest.funding_rate_details if latest else None,

            signal_data_stale=False,
        )

        db.add(new_state)
        db.commit()

        logger.info(
            f"signal_state updated (slow): "
            f"macro={new_state.macro_draining} "
            f"abandonment={new_state.any_abandonment} "
            f"regulatory={new_state.regulatory_pressure} "
            f"unlock={new_state.major_unlock_imminent}"
        )

    except Exception as e:
        logger.error(f"_update_signal_state error: {e}")
        db.rollback()


def _broadcast_signal_update(results: Dict[str, Any]) -> None:
    """
    Broadcasts slow signal update event.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "signal_update",
            "signal_type": "slow",
            "data": {
                "macro_draining": results.get(
                    "macro_draining", False
                ),
                "weekly_delta_pct": results.get(
                    "weekly_delta_pct", 0.0
                ),
                "any_abandonment": results.get(
                    "any_abandonment", False
                ),
                "regulatory_pressure": results.get(
                    "regulatory_pressure", False
                ),
                "total_dockets_7d": results.get(
                    "total_dockets_7d", 0
                ),
                "major_unlock_imminent": results.get(
                    "major_unlock_imminent", False
                ),
                "upcoming_unlocks": results.get(
                    "upcoming_unlocks", []
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