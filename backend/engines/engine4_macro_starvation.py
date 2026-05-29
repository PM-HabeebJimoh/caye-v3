"""
CAYE v3.0 — Engine 4: Macro Starvation Short
Targets optimistic price milestone markets where
Federal Reserve net liquidity data proves the
price target is mathematically unreachable.
Crypto cannot pump without liquidity expansion.
"""

from typing import Dict, Any
from loguru import logger

from backend.engines.base import BaseEngine, EngineResult, SignalState


class Engine4MacroStarvation(BaseEngine):
    """
    Engine 4: Macro Starvation Short

    WHAT IT TARGETS:
    Bullish price milestone markets
    ("Will BTC reach $X?", "Will ETH hit new ATH?")
    where FRED data shows net liquidity contracting
    > 2% weekly, making the target mathematically
    impossible in the resolution timeframe.

    CIS FORMULA:
    Macro Draining       +0.40 (Primary)
    Stablecoin Exodus    +0.30 (Primary)
    Over-Leveraged       +0.20 (Supporting)
    Dev Abandonment      +0.10 (Supporting)
    Max: 1.00

    MINIMUM FOR CIS >= 0.89:
    Macro + Stablecoin + Leverage = 0.90 ✓
    """

    ENGINE_ID = 4
    ENGINE_NAME = "Macro Starvation Short"

    def evaluate(
        self,
        market: Dict[str, Any],
        signal_state: SignalState,
        spot_prices: Dict[str, Any],
        bankroll: float = 10000.0
    ) -> EngineResult:
        """
        Evaluates market for Macro Starvation opportunity.

        Conditions:
        - subcategory == PRICE_MILESTONE_BULL
        - NO side <= 0.52 (we buy NO — target won't be reached)
        - CIS >= 0.89 primarily driven by macro_draining
        """
        result = self._build_base_result(market)
        subcategory = result.subcategory
        no_price = result.no_price
        yes_price = result.yes_price

        # ─────────────────────────────────────
        # VERIFY BULLISH PRICE MILESTONE
        # ─────────────────────────────────────
        if subcategory != "PRICE_MILESTONE_BULL":
            return self._skip(
                result,
                f"Subcategory '{subcategory}' is not "
                f"PRICE_MILESTONE_BULL"
            )

        # ─────────────────────────────────────
        # VERIFY NO SIDE IS BUYABLE
        # (Market is pricing YES too high — retail
        # is too bullish — we buy NO)
        # ─────────────────────────────────────
        if no_price > self.PRICE_CEILING:
            return self._skip(
                result,
                f"NO price ${no_price:.3f} > "
                f"${self.PRICE_CEILING} ceiling. "
                f"Already priced in — ROI insufficient."
            )

        if no_price <= 0:
            return self._skip(
                result,
                f"NO price ${no_price:.3f} invalid"
            )

        # ─────────────────────────────────────
        # SET ENTRY: BUY NO
        # (Bullish target will NOT be reached)
        # ─────────────────────────────────────
        entry_price = no_price
        target_side = "NO"

        result.entry_price = entry_price
        result.target_side = target_side

        logger.debug(
            f"Engine4: PRICE_MILESTONE_BULL "
            f"YES={yes_price:.3f} (retail consensus) "
            f"NO={no_price:.3f} (our entry) "
            f"question='{result.question[:60]}...'"
        )

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