"""
CAYE v3.0 — Task 1: scan_markets
Runs every 60 seconds.
Core orchestration task.

FLOW:
1. Fetch all Polymarket markets (Signal 1)
2. Apply 6-layer crypto filter
3. Load current signal state from DB
4. For each crypto market:
   a. Route to correct engine
   b. Evaluate all 4 gates
   c. Calculate CIS score
   d. Calculate Kelly position size
   e. Save opportunity to DB
   f. Broadcast via WebSocket
5. Log scan results
6. Broadcast scan_complete event
"""

import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.config import get_settings

settings = get_settings()
logger = get_task_logger(__name__)


@celery_app.task(
    name="backend.tasks.scan_markets.scan_markets",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    soft_time_limit=110,
    time_limit=120,
)
def scan_markets(self):
    """
    Main market scanning task.
    Runs every 60 seconds via Celery Beat.
    Orchestrates all 4 engines across all
    active Polymarket crypto markets.
    """
    scan_start = time.time()
    scan_start_dt = datetime.utcnow()

    # ─────────────────────────────────────────
    # INITIALIZE COUNTERS
    # ─────────────────────────────────────────
    counters = {
        "markets_fetched": 0,
        "markets_crypto": 0,
        "markets_vetoed": 0,
        "opportunities_found": 0,
        "gate1_vetoed": 0,
        "gate2_vetoed": 0,
        "gate3_vetoed": 0,
        "gate4_vetoed": 0,
    }

    db = SessionLocal()
    error_message = None

    try:
        # ─────────────────────────────────────
        # STEP 1: LOAD SIGNAL STATE FROM DB
        # ─────────────────────────────────────
        signal_state = _load_signal_state(db)

        if signal_state.signal_data_stale:
            logger.warning(
                "scan_markets: signal data is stale — "
                "CIS calculations may be conservative"
            )

        # ─────────────────────────────────────
        # STEP 2: LOAD SPOT PRICES FROM CACHE
        # ─────────────────────────────────────
        spot_prices = _load_spot_prices()

        # ─────────────────────────────────────
        # STEP 3: FETCH ALL POLYMARKET MARKETS
        # ─────────────────────────────────────
        markets = asyncio.run(_fetch_markets())
        counters["markets_fetched"] = len(markets)

        logger.info(
            f"scan_markets: fetched "
            f"{len(markets)} crypto markets"
        )

        if not markets:
            logger.warning(
                "scan_markets: no markets returned "
                "from Polymarket API"
            )
            _save_scan_log(
                db, scan_start_dt, counters,
                True, "No markets from Polymarket API"
            )
            return counters

        counters["markets_crypto"] = len(markets)

        # ─────────────────────────────────────
        # STEP 4: PROCESS EACH MARKET
        # ─────────────────────────────────────
        from backend.engines.router import EngineRouter
        from backend.engines.engine1_inverse_trap import (
            Engine1InverseTrap
        )
        from backend.engines.engine2_tail_risk import (
            Engine2TailRisk
        )
        from backend.engines.engine3_unlock_bleed import (
            Engine3UnlockBleed
        )
        from backend.engines.engine4_macro_starvation import (
            Engine4MacroStarvation
        )

        router = EngineRouter()
        engines = {
            1: Engine1InverseTrap(),
            2: Engine2TailRisk(),
            3: Engine3UnlockBleed(),
            4: Engine4MacroStarvation(),
        }

        bankroll = settings.default_bankroll

        for market in markets:
            result = _process_market(
                market=market,
                router=router,
                engines=engines,
                signal_state=signal_state,
                spot_prices=spot_prices,
                bankroll=bankroll,
                db=db,
                counters=counters
            )

        # ─────────────────────────────────────
        # STEP 5: SAVE SCAN LOG
        # ─────────────────────────────────────
        scan_duration_ms = int(
            (time.time() - scan_start) * 1000
        )

        _save_scan_log(
            db=db,
            scanned_at=scan_start_dt,
            counters=counters,
            signal_data_stale=signal_state.signal_data_stale,
            error_message=error_message,
            duration_ms=scan_duration_ms
        )

        # ─────────────────────────────────────
        # STEP 6: BROADCAST scan_complete
        # ─────────────────────────────────────
        _broadcast_scan_complete(counters, scan_duration_ms)

        logger.info(
            f"scan_markets COMPLETE: "
            f"fetched={counters['markets_fetched']} "
            f"crypto={counters['markets_crypto']} "
            f"vetoed={counters['markets_vetoed']} "
            f"found={counters['opportunities_found']} "
            f"duration={scan_duration_ms}ms"
        )

        return counters

    except Exception as e:
        error_message = str(e)
        logger.error(f"scan_markets FAILED: {e}")

        _save_scan_log(
            db=db,
            scanned_at=scan_start_dt,
            counters=counters,
            signal_data_stale=True,
            error_message=error_message
        )

        try:
            raise self.retry(exc=e, countdown=10)
        except self.MaxRetriesExceededError:
            logger.error(
                "scan_markets: max retries exceeded"
            )
            return counters

    finally:
        db.close()


# ─────────────────────────────────────────
# PROCESS SINGLE MARKET
# ─────────────────────────────────────────

def _process_market(
    market: Dict[str, Any],
    router,
    engines: Dict,
    signal_state,
    spot_prices: Dict,
    bankroll: float,
    db,
    counters: Dict
) -> None:
    """
    Processes a single market through the
    full engine pipeline.
    Saves opportunity or veto log to DB.
    """
    try:
        # Route to engine
        engine_id, target_side, skip_reason = router.route(
            market, signal_state
        )

        if engine_id is None:
            # No applicable engine — silent skip
            return

        # Get the engine
        engine = engines.get(engine_id)
        if not engine:
            logger.error(
                f"No engine found for id={engine_id}"
            )
            return

        # Override target_side from router
        market["_router_target_side"] = target_side

        # Evaluate through engine
        result = engine.evaluate(
            market=market,
            signal_state=signal_state,
            spot_prices=spot_prices,
            bankroll=bankroll
        )

        # Handle skip (engine said not applicable)
        if result.should_skip:
            return

        # Handle gate veto
        if not result.all_gates_passed:
            counters["markets_vetoed"] += 1

            # Track which gate failed
            gate = result.vetoed_by_gate
            if gate == 1:
                counters["gate1_vetoed"] += 1
            elif gate == 2:
                counters["gate2_vetoed"] += 1
            elif gate == 3:
                counters["gate3_vetoed"] += 1
            elif gate == 4:
                counters["gate4_vetoed"] += 1

            # Save veto log
            _save_veto_log(db, result, market)
            return

        # All gates passed — save opportunity
        _save_opportunity(db, result, market)
        counters["opportunities_found"] += 1

        # Broadcast new opportunity
        _broadcast_new_opportunity(result)

    except Exception as e:
        logger.warning(
            f"_process_market error for "
            f"'{market.get('question', '')[:50]}': {e}"
        )


# ─────────────────────────────────────────
# HELPER: LOAD SIGNAL STATE
# ─────────────────────────────────────────

def _load_signal_state(db):
    """
    Loads latest signal state from DB.
    Returns SignalState dataclass.
    Flags as stale if older than 6 hours.
    """
    from backend.models import SignalState as SignalStateModel
    from backend.engines.base import SignalState
    from sqlalchemy import desc
    from datetime import timedelta

    record = db.query(SignalStateModel).order_by(
        desc(SignalStateModel.created_at)
    ).first()

    if not record:
        logger.warning(
            "_load_signal_state: no record found, "
            "using safe defaults"
        )
        return SignalState(signal_data_stale=True)

    # Check freshness (6 hour threshold)
    age_threshold = datetime.utcnow() - timedelta(hours=6)
    is_stale = False

    if record.created_at:
        record_time = record.created_at.replace(tzinfo=None)
        if record_time < age_threshold:
            is_stale = True
            logger.warning(
                f"_load_signal_state: data is stale "
                f"(last updated: {record.created_at})"
            )

    state = SignalState.from_db_record(record)
    state.signal_data_stale = is_stale
    return state


# ─────────────────────────────────────────
# HELPER: LOAD SPOT PRICES
# ─────────────────────────────────────────

def _load_spot_prices() -> Dict[str, Any]:
    """
    Loads latest spot prices from Redis cache.
    Returns empty dict if unavailable.
    """
    try:
        from backend.signals.cache import cache
        cached = cache.get("coingecko_prices")
        if cached:
            return cached
        logger.warning(
            "_load_spot_prices: no cached prices available"
        )
        return {}
    except Exception as e:
        logger.warning(f"_load_spot_prices error: {e}")
        return {}


# ─────────────────────────────────────────
# HELPER: FETCH MARKETS
# ─────────────────────────────────────────

async def _fetch_markets() -> List[Dict[str, Any]]:
    """
    Fetches all active Polymarket crypto markets.
    """
    from backend.signals.polymarket import PolymarketSignal
    signal = PolymarketSignal()
    return await signal.fetch_all_markets()


# ─────────────────────────────────────────
# HELPER: SAVE OPPORTUNITY
# ─────────────────────────────────────────

def _save_opportunity(db, result, market: Dict) -> None:
    """
    Saves a passing opportunity to the DB.
    Skips if duplicate market_id already active.
    """
    try:
        from backend.models import Opportunity
        from sqlalchemy import and_

        # Check for existing active opportunity
        existing = db.query(Opportunity).filter(
            and_(
                Opportunity.market_id == result.market_id,
                Opportunity.status == "ACTIVE"
            )
        ).first()

        if existing:
            # Update CIS and position if changed
            if abs(existing.cis_score - result.cis_score) > 0.01:
                existing.cis_score = result.cis_score
                existing.signal_breakdown = result.signal_breakdown
                existing.recommended_position = (
                    result.recommended_position
                )
                existing.potential_profit = result.potential_profit
                db.commit()
                logger.debug(
                    f"Updated existing opportunity: "
                    f"{result.market_id[:20]}... "
                    f"new CIS={result.cis_score:.4f}"
                )
            return

        # Create new opportunity
        opportunity = Opportunity(
            market_id=result.market_id,
            condition_id=market.get("condition_id"),
            question=result.question,
            polymarket_url=result.polymarket_url,
            market_category="CRYPTO",
            subcategory=result.subcategory,
            engine_id=result.engine_id,
            engine_name=result.engine_name,
            entry_price=result.entry_price,
            target_side=result.target_side,
            yes_price_at_entry=result.yes_price,
            no_price_at_entry=result.no_price,
            cis_score=result.cis_score,
            signal_breakdown=result.signal_breakdown,
            gate_results={
                "gate1_passed": result.gate1_passed,
                "gate1_reason": result.gate1_reason,
                "gate2_passed": result.gate2_passed,
                "gate2_reason": result.gate2_reason,
                "gate3_passed": result.gate3_passed,
                "gate3_reason": result.gate3_reason,
                "gate4_passed": result.gate4_passed,
                "gate4_reason": result.gate4_reason,
            },
            recommended_position=result.recommended_position,
            potential_profit=result.potential_profit,
            roi_pct=result.roi_pct,
            kelly_fraction=result.kelly_fraction,
            expected_value=result.expected_value,
            liquidity=result.liquidity,
            volume=result.volume,
            expiry_date=_parse_datetime(result.expiry_date),
            days_to_expiry=result.days_to_expiry,
            status="ACTIVE",
        )

        db.add(opportunity)
        db.commit()
        db.refresh(opportunity)

        logger.info(
            f"NEW OPPORTUNITY SAVED: "
            f"Engine {result.engine_id} "
            f"[{result.engine_name}] "
            f"CIS={result.cis_score:.4f} "
            f"Entry=${result.entry_price:.2f} "
            f"Side={result.target_side} "
            f"ROI={result.roi_pct:.1f}%"
        )

    except Exception as e:
        logger.error(f"_save_opportunity error: {e}")
        db.rollback()


# ─────────────────────────────────────────
# HELPER: SAVE VETO LOG
# ─────────────────────────────────────────

def _save_veto_log(db, result, market: Dict) -> None:
    """
    Saves gate veto to veto_log table.
    Records exact reason for transparency.
    """
    try:
        from backend.models import VetoLog

        gate_names = {
            1: "Price Ceiling",
            2: "CIS Threshold",
            3: "Liquidity Minimum",
            4: "Expiry Guard"
        }

        gate_num = result.vetoed_by_gate or 0
        gate_name = gate_names.get(gate_num, "Unknown")

        # Determine actual_value based on gate
        actual_value = None
        required_value = None

        if gate_num == 1:
            actual_value = result.entry_price
            required_value = 0.52
        elif gate_num == 2:
            actual_value = result.cis_score
            required_value = 0.89
        elif gate_num == 3:
            actual_value = result.liquidity
            required_value = 50000.0
        elif gate_num == 4:
            actual_value = float(
                result.days_to_expiry or 0
            )
            required_value = 2.0

        veto = VetoLog(
            market_id=result.market_id,
            question=result.question[:500] if result.question else None,
            gate_number=gate_num,
            gate_name=gate_name,
            reason=result.veto_reason[:1000] if result.veto_reason else "",
            actual_value=actual_value,
            required_value=required_value,
            entry_price=result.entry_price,
            engine_id=result.engine_id,
            cis_score=result.cis_score if result.cis_score else None,
            signal_breakdown=result.signal_breakdown if result.signal_breakdown else None,
        )

        db.add(veto)
        db.commit()

    except Exception as e:
        logger.warning(f"_save_veto_log error: {e}")
        db.rollback()


# ─────────────────────────────────────────
# HELPER: SAVE SCAN LOG
# ─────────────────────────────────────────

def _save_scan_log(
    db,
    scanned_at: datetime,
    counters: Dict,
    signal_data_stale: bool = False,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None
) -> None:
    """
    Saves scan run statistics to scan_log table.
    """
    try:
        from backend.models import ScanLog

        log = ScanLog(
            scanned_at=scanned_at,
            markets_fetched=counters.get("markets_fetched", 0),
            markets_crypto=counters.get("markets_crypto", 0),
            markets_vetoed=counters.get("markets_vetoed", 0),
            opportunities_found=counters.get(
                "opportunities_found", 0
            ),
            gate1_vetoed=counters.get("gate1_vetoed", 0),
            gate2_vetoed=counters.get("gate2_vetoed", 0),
            gate3_vetoed=counters.get("gate3_vetoed", 0),
            gate4_vetoed=counters.get("gate4_vetoed", 0),
            scan_duration_ms=duration_ms,
            signal_data_stale=signal_data_stale,
            error_message=error_message,
        )

        db.add(log)
        db.commit()

    except Exception as e:
        logger.warning(f"_save_scan_log error: {e}")
        db.rollback()


# ─────────────────────────────────────────
# HELPER: BROADCAST NEW OPPORTUNITY
# ─────────────────────────────────────────

def _broadcast_new_opportunity(result) -> None:
    """
    Broadcasts new opportunity via WebSocket.
    Phase 6 WebSocket manager handles delivery.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "new_opportunity",
            "opportunity": result.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }

        cache._get_redis()
        r = cache._get_redis()
        if r:
            r.publish(
                "caye_events",
                json.dumps(event, default=str)
            )

    except Exception as e:
        logger.debug(
            f"_broadcast_new_opportunity: {e} "
            f"(WebSocket not yet connected)"
        )


# ─────────────────────────────────────────
# HELPER: BROADCAST SCAN COMPLETE
# ─────────────────────────────────────────

def _broadcast_scan_complete(
    counters: Dict,
    duration_ms: int
) -> None:
    """
    Broadcasts scan_complete event via WebSocket.
    """
    try:
        from backend.signals.cache import cache
        import json

        event = {
            "event": "scan_complete",
            "scan_log": {
                **counters,
                "scan_duration_ms": duration_ms,
                "scanned_at": datetime.utcnow().isoformat()
            }
        }

        r = cache._get_redis()
        if r:
            r.publish(
                "caye_events",
                json.dumps(event, default=str)
            )

    except Exception as e:
        logger.debug(f"_broadcast_scan_complete: {e}")


# ─────────────────────────────────────────
# HELPER: PARSE DATETIME STRING
# ─────────────────────────────────────────

def _parse_datetime(dt_str: Optional[str]):
    """
    Parses ISO datetime string to datetime object.
    Returns None if invalid.
    """
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(
            dt_str.replace("Z", "+00:00")
        )
    except Exception:
        return None