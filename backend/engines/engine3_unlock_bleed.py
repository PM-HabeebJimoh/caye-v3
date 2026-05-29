"""
CAYE v3.0 — Engine 3: Deterministic Unlock Bleed
Targets token price markets where scheduled
vesting cliff unlocks > $50M are imminent.
The sell pressure is DETERMINISTIC.
The unlock WILL happen. The pressure WILL occur.
Only the magnitude varies — not the direction.
"""

from typing import Dict, Any, Optional
from loguru import logger

from backend.engines.base import BaseEngine, EngineResult, SignalState


class Engine3UnlockBleed(BaseEngine):
    """
    Engine 3: Deterministic Unlock Bleed

    WHAT IT TARGETS:
    Token price markets where:
    - A major vesting cliff unlock is imminent (< 7 days)
    - Current spot price is ABOVE the market's price target
    - The unlock will create guaranteed downward pressure
    - Market is asking: "Will [token] be below [price]?"

    CIS FORMULA:
    Major Unlock Imminent  +0.45 (Primary)
    Stablecoin Exodus      +0.25 (Important)
    Over-Leveraged         +0.20 (Supporting)
    Macro Draining         +0.10 (Supporting)
    Max: 1.00

    MINIMUM FOR CIS >= 0.89:
    Unlock + Stablecoin + Leverage = 0.90 ✓

    ENTRY TIMING RULE:
    Enter 1-3 days BEFORE unlock date.
    Never enter on day of unlock.
    """

    ENGINE_ID = 3
    ENGINE_NAME = "Deterministic Unlock Bleed"

    def evaluate(
        self,
        market: Dict[str, Any],
        signal_state: SignalState,
        spot_prices: Dict[str, Any],
        bankroll: float = 10000.0
    ) -> EngineResult:
        """
        Evaluates market for Unlock Bleed opportunity.

        Conditions:
        - subcategory == TOKEN_UNLOCK
        - major_unlock_imminent == True
        - Current spot price > market price target
        - YES price <= 0.52 (Gate 1)
        """
        result = self._build_base_result(market)
        subcategory = result.subcategory

        # ─────────────────────────────────────
        # VERIFY TOKEN UNLOCK SUBCATEGORY
        # ─────────────────────────────────────
        if subcategory != "TOKEN_UNLOCK":
            return self._skip(
                result,
                f"Subcategory '{subcategory}' is not "
                f"TOKEN_UNLOCK"
            )

        # ─────────────────────────────────────
        # VERIFY MAJOR UNLOCK IS IMMINENT
        # ─────────────────────────────────────
        if not signal_state.major_unlock_imminent:
            return self._skip(
                result,
                "major_unlock_imminent = False. "
                "No qualifying unlock within 7 days."
            )

        # ─────────────────────────────────────
        # EXTRACT TOKEN AND PRICE TARGET
        # ─────────────────────────────────────
        token_symbol = market.get("token_symbol")
        price_target = market.get("price_target")

        if not token_symbol:
            return self._skip(
                result,
                "Could not extract token symbol from question"
            )

        if not price_target or price_target <= 0:
            return self._skip(
                result,
                "Could not extract price target from question"
            )

        # ─────────────────────────────────────
        # VERIFY CURRENT PRICE > TARGET
        # Only valid if price can still drop below target
        # ─────────────────────────────────────
        current_price = self._get_current_price(
            token_symbol, spot_prices
        )

        if current_price is None or current_price <= 0:
            return self._skip(
                result,
                f"Could not get current price for "
                f"{token_symbol}"
            )

        if current_price <= price_target:
            return self._skip(
                result,
                f"{token_symbol} current price "
                f"${current_price:.4f} already "
                f"<= target ${price_target:.4f}. "
                f"Thesis already resolved."
            )

        # ─────────────────────────────────────
        # SET ENTRY: BUY YES (price WILL drop)
        # YES = "will be below price target"
        # ─────────────────────────────────────
        entry_price = float(market.get("yes_price", 0.5))
        target_side = "YES"

        result.entry_price = entry_price
        result.target_side = target_side

        # Store extra context for display
        distance_pct = (
            (current_price - price_target) / price_target * 100
        )
        logger.debug(
            f"Engine3: {token_symbol} "
            f"current=${current_price:.4f} "
            f"target=${price_target:.4f} "
            f"distance={distance_pct:.1f}% above target"
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

    def _get_current_price(
        self,
        token_symbol: str,
        spot_prices: Dict[str, Any]
    ) -> Optional[float]:
        """
        Gets current spot price for token symbol.
        Searches CoinGecko price data by symbol.
        """
        if not spot_prices:
            return None

        symbol_upper = token_symbol.upper()

        for token_id, data in spot_prices.items():
            stored_symbol = data.get("symbol", "").upper()
            if stored_symbol == symbol_upper:
                price = data.get("price", 0)
                return float(price) if price else None

        # Try direct token_id lookup
        token_id_map = {
            "ARB": "arbitrum",
            "APT": "aptos",
            "OP": "optimism",
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }

        coingecko_id = token_id_map.get(symbol_upper)
        if coingecko_id and coingecko_id in spot_prices:
            price = spot_prices[coingecko_id].get("price", 0)
            return float(price) if price else None

        return None