"""
CAYE v3.0 — Engine 1: Inverse Trap
Targets markets where extreme retail consensus
has pushed one side above $0.80, making the
inverse contract priced <= $0.20.
Retail overcorrection = structural mispricing.
"""

from typing import Dict, Any
from loguru import logger

from backend.engines.base import BaseEngine, EngineResult, SignalState


class Engine1InverseTrap(BaseEngine):
    """
    Engine 1: Inverse Trap

    WHAT IT TARGETS:
    Polymarket crypto markets where retail extreme
    consensus has pushed one side > $0.80, making
    the inverse contract priced <= $0.20.

    CIS FORMULA:
    Stablecoin Exodus  +0.35
    Macro Draining     +0.25
    Over-Leveraged     +0.20
    Dev Abandonment    +0.15
    Regulatory Press   +0.05
    Max: 1.00

    MINIMUM FOR CIS >= 0.89:
    Stablecoin + Macro + Leverage + Abandonment = 0.95 ✓
    """

    ENGINE_ID = 1
    ENGINE_NAME = "Inverse Trap"

    # Engine 1 specific thresholds
    CONSENSUS_THRESHOLD = 0.80   # Side must be > this
    INVERSE_MAX_PRICE = 0.52     # Inverse must be <= this

    def evaluate(
        self,
        market: Dict[str, Any],
        signal_state: SignalState,
        spot_prices: Dict[str, Any],
        bankroll: float = 10000.0
    ) -> EngineResult:
        """
        Evaluates market for Inverse Trap opportunity.

        Conditions:
        A: YES > 0.80 AND NO <= 0.52 → BUY NO
        B: NO > 0.80 AND YES <= 0.52 → BUY YES
        """
        result = self._build_base_result(market)

        yes_price = result.yes_price
        no_price = result.no_price

        # ─────────────────────────────────────
        # DETERMINE ENTRY SIDE AND PRICE
        # ─────────────────────────────────────
        entry_price = None
        target_side = None

        # Condition A: Retail too bullish → BUY NO
        if (yes_price > self.CONSENSUS_THRESHOLD
                and no_price <= self.INVERSE_MAX_PRICE):
            entry_price = no_price
            target_side = "NO"

        # Condition B: Retail too bearish → BUY YES
        elif (no_price > self.CONSENSUS_THRESHOLD
              and yes_price <= self.INVERSE_MAX_PRICE):
            entry_price = yes_price
            target_side = "YES"

        # No inverse trap pattern found
        else:
            return self._skip(
                result,
                f"No extreme consensus: "
                f"YES={yes_price:.3f} NO={no_price:.3f} "
                f"(need one side > {self.CONSENSUS_THRESHOLD})"
            )

        result.entry_price = entry_price
        result.target_side = target_side

        # ─────────────────────────────────────
        # GATE 3: LIQUIDITY CHECK
        # ─────────────────────────────────────
        if not self._enforce_gate3_liquidity(result):
            return result

        # ─────────────────────────────────────
        # GATE 1: PRICE CEILING CHECK
        # ─────────────────────────────────────
        if not self._enforce_gate1_price(result, entry_price):
            return result

        # ─────────────────────────────────────
        # GATE 4: EXPIRY CHECK
        # ─────────────────────────────────────
        if not self._enforce_gate4_expiry(result):
            return result

        # ─────────────────────────────────────
        # GATE 2: CIS THRESHOLD CHECK
        # ─────────────────────────────────────
        cis_score, breakdown = self.cis_calculator.calculate(
            engine_id=self.ENGINE_ID,
            signal_state=signal_state
        )

        if not self._enforce_gate2_cis(result, cis_score, breakdown):
            return result

        # ─────────────────────────────────────
        # ALL GATES PASSED → SIZE POSITION
        # ─────────────────────────────────────
        self._apply_kelly_sizing(
            result, entry_price, cis_score, bankroll
        )

        return self._finalize_pass(result)