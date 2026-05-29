"""
CAYE v3.0 — Engine Router
Routes each market to the correct engine
based on subcategory and market structure.
Engine 2 checked first (tail risk priority).
Returns engine_id or SKIP with reason.
"""

from typing import Dict, Any, Optional, Tuple
from loguru import logger

from backend.engines.base import SignalState


# Engine name mapping
ENGINE_NAMES = {
    1: "Inverse Trap",
    2: "Tail-Risk Front-Run",
    3: "Deterministic Unlock Bleed",
    4: "Macro Starvation Short",
}

# Engine 2 subcategories
ENGINE2_SUBCATEGORIES = [
    "EXCHANGE_SOLVENCY",
    "PROTOCOL_HACK",
    "STABLECOIN_DEPEG",
    "FOUNDER_ACTION",
]


class EngineRouter:
    """
    Routes markets to the appropriate engine.
    Routing order: E2 → E3 → E4 → E1 → SKIP
    Engine 2 has highest priority (tail risk).
    """

    def route(
        self,
        market: Dict[str, Any],
        signal_state: SignalState
    ) -> Tuple[Optional[int], str, Optional[str]]:
        """
        Routes a market to the correct engine.

        Args:
            market: Parsed market dict from Signal 1
            signal_state: Current signal booleans

        Returns:
            Tuple of:
            - engine_id (1-4) or None if skip
            - target_side ('YES' or 'NO') or ''
            - skip_reason if None engine_id
        """
        subcategory = market.get("subcategory", "GENERAL_CRYPTO")
        yes_price = float(market.get("yes_price", 0.5))
        no_price = float(market.get("no_price", 0.5))

        # ─────────────────────────────────────
        # ENGINE 2: TAIL-RISK FRONT-RUN
        # Highest priority check
        # ─────────────────────────────────────
        if subcategory in ENGINE2_SUBCATEGORIES:
            if yes_price <= 0.15:
                logger.debug(
                    f"Router: E2 match — "
                    f"{subcategory} YES@{yes_price:.3f}"
                )
                return 2, "YES", None

            if no_price <= 0.15:
                logger.debug(
                    f"Router: E2 match — "
                    f"{subcategory} NO@{no_price:.3f}"
                )
                return 2, "NO", None

            # Subcategory matches but price too high
            logger.debug(
                f"Router: E2 skip — "
                f"{subcategory} but prices too high "
                f"(YES={yes_price:.2f} NO={no_price:.2f})"
            )

        # ─────────────────────────────────────
        # ENGINE 3: DETERMINISTIC UNLOCK BLEED
        # Token unlock + price threshold market
        # ─────────────────────────────────────
        if subcategory == "TOKEN_UNLOCK":
            if not signal_state.major_unlock_imminent:
                logger.debug(
                    f"Router: E3 skip — "
                    f"TOKEN_UNLOCK market but "
                    f"major_unlock_imminent=False"
                )
            else:
                token_symbol = market.get("token_symbol")
                price_target = market.get("price_target")

                if token_symbol and price_target:
                    # Engine 3 will verify price above target
                    logger.debug(
                        f"Router: E3 match — "
                        f"TOKEN_UNLOCK "
                        f"token={token_symbol} "
                        f"target={price_target}"
                    )
                    return 3, "YES", None
                else:
                    logger.debug(
                        f"Router: E3 skip — "
                        f"could not extract "
                        f"token/price from question"
                    )

        # ─────────────────────────────────────
        # ENGINE 4: MACRO STARVATION SHORT
        # Bullish price milestone + NO side
        # ─────────────────────────────────────
        if subcategory == "PRICE_MILESTONE_BULL":
            if no_price <= 0.52:
                logger.debug(
                    f"Router: E4 match — "
                    f"PRICE_MILESTONE_BULL "
                    f"NO@{no_price:.3f}"
                )
                return 4, "NO", None
            else:
                logger.debug(
                    f"Router: E4 skip — "
                    f"PRICE_MILESTONE_BULL but "
                    f"NO price ${no_price:.2f} > $0.52"
                )

        # ─────────────────────────────────────
        # ENGINE 1: INVERSE TRAP
        # Extreme consensus on either side
        # ─────────────────────────────────────
        if yes_price > 0.80 and no_price <= 0.52:
            logger.debug(
                f"Router: E1 match — "
                f"YES={yes_price:.2f} > 0.80, "
                f"BUY NO@{no_price:.3f}"
            )
            return 1, "NO", None

        if no_price > 0.80 and yes_price <= 0.52:
            logger.debug(
                f"Router: E1 match — "
                f"NO={no_price:.2f} > 0.80, "
                f"BUY YES@{yes_price:.3f}"
            )
            return 1, "YES", None

        # ─────────────────────────────────────
        # NO ENGINE MATCHED
        # ─────────────────────────────────────
        skip_reason = (
            f"No structural inefficiency pattern. "
            f"Subcategory={subcategory} "
            f"YES={yes_price:.3f} "
            f"NO={no_price:.3f}"
        )
        logger.debug(f"Router: SKIP — {skip_reason}")
        return None, "", skip_reason

    def get_engine_name(self, engine_id: int) -> str:
        """
        Returns display name for engine ID.
        """
        return ENGINE_NAMES.get(engine_id, "Unknown")