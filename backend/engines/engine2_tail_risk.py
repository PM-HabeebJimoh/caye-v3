"""
CAYE v3.0 — Engine 2: Tail-Risk Front-Run
Targets low-probability tail-risk events
priced <= $0.15 where structural signals
indicate true probability is >> market price.
Retail assumes safety. Hidden data proves danger.
"""

from typing import Dict, Any
from loguru import logger

from backend.engines.base import BaseEngine, EngineResult, SignalState


# Engine 2 target subcategories
TARGET_SUBCATEGORIES = [
    "EXCHANGE_SOLVENCY",
    "PROTOCOL_HACK",
    "STABLECOIN_DEPEG",
    "FOUNDER_ACTION",
]


class Engine2TailRisk(BaseEngine):
    """
    Engine 2: Tail-Risk Front-Run

    WHAT IT TARGETS:
    Low-probability events priced <= $0.15 where
    developer abandonment + insider gas activity +
    regulatory pressure signals prove the true
    probability is much higher than market pricing.

    CIS FORMULA:
    Dev Abandonment    +0.35 (Primary)
    Insider Activity   +0.30 (Strong)
    Regulatory Press   +0.25 (Strong)
    Stablecoin Exodus  +0.10 (Supporting)
    Max: 1.00

    MINIMUM FOR CIS >= 0.89:
    Abandonment + Insider + Regulatory = 0.90 ✓
    """

    ENGINE_ID = 2
    ENGINE_NAME = "Tail-Risk Front-Run"

    # Engine 2 specific threshold
    TAIL_RISK_MAX_PRICE = 0.15   # Must be priced <= this

    def evaluate(
        self,
        market: Dict[str, Any],
        signal_state: SignalState,
        spot_prices: Dict[str, Any],
        bankroll: float = 10000.0
    ) -> EngineResult:
        """
        Evaluates market for Tail-Risk opportunity.

        Conditions:
        - subcategory in target list
        - YES <= 0.15 OR NO <= 0.15
        - CIS >= 0.89 from structural signals
        """
        result = self._build_base_result(market)
        subcategory = result.subcategory
        yes_price = result.yes_price
        no_price = result.no_price

        # ─────────────────────────────────────
        # VERIFY TARGET SUBCATEGORY
        # ─────────────────────────────────────
        if subcategory not in TARGET_SUBCATEGORIES:
            return self._skip(
                result,
                f"Subcategory '{subcategory}' not a "
                f"tail-risk target. Need: {TARGET_SUBCATEGORIES}"
            )

        # ─────────────────────────────────────
        # FIND THE TAIL-RISK SIDE (<= $0.15)
        # ─────────────────────────────────────
        entry_price = None
        target_side = None

        if yes_price <= self.TAIL_RISK_MAX_PRICE:
            entry_price = yes_price
            target_side = "YES"
        elif no_price <= self.TAIL_RISK_MAX_PRICE:
            entry_price = no_price
            target_side = "NO"
        else:
            return self._skip(
                result,
                f"Neither side priced as tail-risk. "
                f"YES=${yes_price:.3f} NO=${no_price:.3f} "
                f"(need one side <= ${self.TAIL_RISK_MAX_PRICE})"
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
        # Entry is already <= $0.15 so always passes
        # but enforce formally
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