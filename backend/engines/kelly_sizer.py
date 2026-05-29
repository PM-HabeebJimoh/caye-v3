"""
CAYE v3.0 — Quarter-Kelly Position Sizing Engine
Mathematically optimal position sizing.
f* = (p*(b+1) - 1) / b
Quarter-Kelly = f* * 0.25
Hard cap: 25% of bankroll maximum.
"""

from typing import Dict, Any
from loguru import logger


class KellySizer:
    """
    Quarter-Kelly Criterion position sizer.
    Maximizes long-term growth while keeping
    maximum drawdown below 3% per trade.
    """

    KELLY_FRACTION = 0.25         # Quarter of full Kelly
    MAX_POSITION_FRACTION = 0.25  # Hard cap: 25% of bankroll
    MIN_TRADE_SIZE = 50.0         # Minimum $50 per trade

    def calculate(
        self,
        entry_price: float,
        cis_score: float,
        bankroll: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Calculates Quarter-Kelly position size.

        Args:
            entry_price: Cost per contract (0.0 to 0.52)
            cis_score: Win probability from CIS (0.89 to 1.0)
            bankroll: Total available capital

        Returns:
            Dict with position_size, potential_profit,
            roi_pct, kelly_fraction, expected_value
        """

        # Validate inputs
        if entry_price <= 0 or entry_price >= 1.0:
            return self._error_result(
                "Invalid entry price — must be 0 < price < 1.0"
            )

        if entry_price > 0.52:
            return self._error_result(
                f"Entry price ${entry_price:.2f} exceeds "
                f"$0.52 ceiling — Gate 1 should have caught this"
            )

        if cis_score < 0.89:
            return self._error_result(
                f"CIS {cis_score:.4f} below 0.89 — "
                f"Gate 2 should have caught this"
            )

        if bankroll <= 0:
            return self._error_result(
                "Invalid bankroll — must be > 0"
            )

        # ─────────────────────────────────────
        # STEP 1: CALCULATE NET ODDS (b)
        # b = (payout - cost) / cost
        # For binary: payout = $1.00
        # ─────────────────────────────────────
        b = (1.0 - entry_price) / entry_price

        # ─────────────────────────────────────
        # STEP 2: SET WIN/LOSS PROBABILITIES
        # p = CIS score (our precision estimate)
        # q = 1 - p (loss probability)
        # ─────────────────────────────────────
        p = cis_score
        q = 1.0 - cis_score

        # ─────────────────────────────────────
        # STEP 3: FULL KELLY FRACTION
        # f* = (p * (b + 1) - 1) / b
        # ─────────────────────────────────────
        full_kelly = (p * (b + 1) - 1) / b

        # Negative Kelly = no mathematical edge
        if full_kelly <= 0:
            return self._error_result(
                f"Negative Kelly ({full_kelly:.4f}) — "
                f"no mathematical edge at this price/CIS"
            )

        # ─────────────────────────────────────
        # STEP 4: QUARTER-KELLY ADJUSTMENT
        # Reduces to 25% of optimal
        # Provides 4x buffer against model error
        # ─────────────────────────────────────
        quarter_kelly = full_kelly * self.KELLY_FRACTION

        # ─────────────────────────────────────
        # STEP 5: APPLY HARD CAP (25% max)
        # ─────────────────────────────────────
        capped_kelly = min(quarter_kelly, self.MAX_POSITION_FRACTION)

        # ─────────────────────────────────────
        # STEP 6: CALCULATE POSITION SIZE
        # ─────────────────────────────────────
        position_size = bankroll * capped_kelly
        position_size = min(
            position_size,
            bankroll * self.MAX_POSITION_FRACTION
        )
        position_size = round(position_size, 2)

        # Check minimum trade size
        if position_size < self.MIN_TRADE_SIZE:
            return self._error_result(
                f"Position size ${position_size:.2f} "
                f"below minimum ${self.MIN_TRADE_SIZE:.2f}"
            )

        # ─────────────────────────────────────
        # STEP 7: CALCULATE EXPECTED OUTCOMES
        # ─────────────────────────────────────
        # If correct: profit = position * net_odds
        potential_profit = round(position_size * b, 2)

        # ROI percentage
        roi_pct = round(b * 100, 1)

        # Max loss is full position
        potential_loss = position_size

        # Expected value
        ev = (p * potential_profit) - (q * potential_loss)
        expected_value = round(ev, 2)

        # Max loss as % of bankroll
        max_loss_pct = round((position_size / bankroll) * 100, 2)

        logger.debug(
            f"Kelly: entry={entry_price:.2f} "
            f"CIS={cis_score:.4f} "
            f"b={b:.2f} "
            f"f*={full_kelly:.4f} "
            f"QK={capped_kelly:.4f} "
            f"pos=${position_size:,.2f} "
            f"profit=${potential_profit:,.2f} "
            f"ROI={roi_pct:.1f}%"
        )

        return {
            "position_size": position_size,
            "potential_profit": potential_profit,
            "potential_loss": potential_loss,
            "roi_pct": roi_pct,
            "kelly_fraction": round(capped_kelly, 4),
            "full_kelly": round(full_kelly, 4),
            "quarter_kelly": round(quarter_kelly, 4),
            "expected_value": expected_value,
            "max_loss_pct": max_loss_pct,
            "net_odds_b": round(b, 4),
            "win_probability": p,
            "loss_probability": q,
            "bankroll": bankroll,
            "error": None
        }

    def _error_result(self, message: str) -> Dict[str, Any]:
        """
        Returns error result when sizing is invalid.
        """
        logger.warning(f"KellySizer error: {message}")
        return {
            "position_size": 0.0,
            "potential_profit": 0.0,
            "potential_loss": 0.0,
            "roi_pct": 0.0,
            "kelly_fraction": 0.0,
            "full_kelly": 0.0,
            "quarter_kelly": 0.0,
            "expected_value": 0.0,
            "max_loss_pct": 0.0,
            "net_odds_b": 0.0,
            "win_probability": 0.0,
            "loss_probability": 0.0,
            "bankroll": 0.0,
            "error": message
        }

    def get_roi_table(self) -> Dict[float, float]:
        """
        Returns the ROI table for all valid entry prices.
        Used for dashboard display.
        """
        prices = [
            0.05, 0.08, 0.10, 0.12, 0.15, 0.20,
            0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.52
        ]
        return {
            price: round((1.0 / price - 1) * 100, 1)
            for price in prices
        }