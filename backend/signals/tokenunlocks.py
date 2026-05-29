"""
CAYE v3.0 — Signal 9: Token Unlocks
DIMENSION: Hidden (35%)
Scheduled vesting cliff unlocks > $50M in 7 days.
Deterministic fallback from smart contract dates.
major_unlock_imminent = True triggers Engine 3.
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class TokenUnlocksSignal:
    """
    Signal 9: Token Unlock Schedule
    Primary: token.unlocks.app API
    Fallback: Deterministic smart contract dates
    APT: 12th of every month
    ARB: 16th of every month
    """

    CACHE_NAMESPACE = "token_unlocks"
    PRIMARY_URL = "https://token.unlocks.app/api/vesting"
    MAX_RETRIES = 3
    UNLOCK_VALUE_THRESHOLD = 50_000_000  # $50M
    DAYS_AHEAD_THRESHOLD = 7
    ENTRY_WINDOW_START = 3  # Enter 3 days before
    ENTRY_WINDOW_END = 1    # Enter 1 day before

    async def fetch_unlock_data(
        self,
        spot_prices: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fetches upcoming token unlocks and identifies
        those meeting the $50M threshold.

        Returns:
            major_unlock_imminent: bool
            upcoming_unlocks: list of unlock events
        """
        # Check cache
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        # Try primary API first
        primary_data = await self._fetch_primary_api()

        if primary_data:
            upcoming = self._process_primary_data(
                primary_data, spot_prices
            )
        else:
            # Use deterministic fallback
            logger.info(
                "TokenUnlocks: using deterministic fallback"
            )
            upcoming = self._calculate_deterministic_unlocks(
                spot_prices
            )

        major_unlock_imminent = len(upcoming) > 0

        # Find entry window opportunities
        entry_opportunities = [
            u for u in upcoming
            if self.ENTRY_WINDOW_END <= u.get(
                "days_until", 0
            ) <= self.ENTRY_WINDOW_START
        ]

        result = {
            "major_unlock_imminent": major_unlock_imminent,
            "upcoming_unlocks": upcoming,
            "entry_window_active": len(entry_opportunities) > 0,
            "entry_opportunities": entry_opportunities,
            "total_upcoming_value": sum(
                u.get("unlock_value_usd", 0)
                for u in upcoming
            )
        }

        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_tokenunlocks
        )

        if major_unlock_imminent:
            for unlock in upcoming:
                logger.warning(
                    f"TokenUnlocks: {unlock['token']} unlock "
                    f"in {unlock['days_until']} days — "
                    f"${unlock['unlock_value_usd']/1e6:.1f}M"
                )
        else:
            logger.info(
                "TokenUnlocks: no major unlocks "
                "in next 7 days"
            )

        return result

    async def _fetch_primary_api(self) -> Optional[Dict]:
        """
        Attempts to fetch from TokenUnlocks primary API.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=15.0
                ) as client:
                    response = await client.get(
                        self.PRIMARY_URL,
                        timeout=15.0
                    )
                    response.raise_for_status()
                    return response.json()

            except Exception as e:
                logger.debug(
                    f"TokenUnlocks primary API: {e} "
                    f"(attempt {attempt + 1}) — "
                    f"will use deterministic fallback"
                )

            if attempt < self.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(2)

        return None

    def _process_primary_data(
        self,
        data: Dict,
        spot_prices: Dict[str, Any]
    ) -> List[Dict]:
        """
        Processes primary API data into
        standardized unlock events.
        """
        upcoming = []
        today = date.today()

        try:
            unlocks = data.get("unlocks", data.get("data", []))

            for unlock in unlocks:
                unlock_date_str = unlock.get("date", "")
                token_symbol = unlock.get(
                    "symbol", unlock.get("token", "")
                ).upper()
                amount = float(
                    unlock.get("amount", 0) or 0
                )

                if not unlock_date_str or not token_symbol:
                    continue

                try:
                    unlock_date = date.fromisoformat(
                        unlock_date_str[:10]
                    )
                except ValueError:
                    continue

                days_until = (unlock_date - today).days

                if days_until < 0 or days_until > self.DAYS_AHEAD_THRESHOLD:
                    continue

                # Get spot price
                spot_price = self._get_spot_price(
                    token_symbol, spot_prices
                )
                unlock_value_usd = amount * spot_price

                if unlock_value_usd < self.UNLOCK_VALUE_THRESHOLD:
                    continue

                upcoming.append({
                    "token": token_symbol,
                    "unlock_date": unlock_date.isoformat(),
                    "days_until": days_until,
                    "unlock_amount": amount,
                    "unlock_value_usd": unlock_value_usd,
                    "spot_price": spot_price,
                    "source": "PRIMARY_API",
                    "in_entry_window": (
                        self.ENTRY_WINDOW_END
                        <= days_until
                        <= self.ENTRY_WINDOW_START
                    )
                })

        except Exception as e:
            logger.warning(
                f"TokenUnlocks primary parse error: {e}"
            )

        return upcoming

    def _calculate_deterministic_unlocks(
        self,
        spot_prices: Dict[str, Any]
    ) -> List[Dict]:
        """
        Calculates upcoming unlocks from deterministic
        smart contract schedule.
        Dates encoded in Ethereum/Solana contracts.
        100% certain — not an estimate.
        """
        upcoming = []
        today = date.today()

        schedule = settings.token_unlock_schedule

        for symbol, config in schedule.items():
            unlock_day = config["unlock_day"]
            unlock_amount = config["unlock_amount"]
            coingecko_id = config["coingecko_id"]

            # Calculate next occurrence
            next_unlock = self._next_occurrence(
                unlock_day, today
            )
            days_until = (next_unlock - today).days

            if days_until > self.DAYS_AHEAD_THRESHOLD:
                continue

            # Get spot price
            spot_price = self._get_spot_price_by_id(
                coingecko_id, spot_prices
            )
            unlock_value_usd = unlock_amount * spot_price

            if unlock_value_usd < self.UNLOCK_VALUE_THRESHOLD:
                logger.info(
                    f"TokenUnlocks {symbol}: "
                    f"unlock value ${unlock_value_usd/1e6:.1f}M "
                    f"below ${self.UNLOCK_VALUE_THRESHOLD/1e6:.0f}M threshold"
                )
                continue

            in_entry_window = (
                self.ENTRY_WINDOW_END
                <= days_until
                <= self.ENTRY_WINDOW_START
            )

            upcoming.append({
                "token": symbol,
                "unlock_date": next_unlock.isoformat(),
                "days_until": days_until,
                "unlock_amount": unlock_amount,
                "unlock_value_usd": unlock_value_usd,
                "spot_price": spot_price,
                "source": "DETERMINISTIC_FALLBACK",
                "in_entry_window": in_entry_window
            })

        return upcoming

    def _next_occurrence(
        self,
        day_of_month: int,
        from_date: date
    ) -> date:
        """
        Calculates the next occurrence of a
        specific day of month.
        """
        # Try current month first
        try:
            candidate = from_date.replace(day=day_of_month)
            if candidate >= from_date:
                return candidate
        except ValueError:
            pass

        # Move to next month
        if from_date.month == 12:
            next_month = from_date.replace(
                year=from_date.year + 1,
                month=1,
                day=day_of_month
            )
        else:
            next_month = from_date.replace(
                month=from_date.month + 1,
                day=day_of_month
            )

        return next_month

    def _get_spot_price(
        self,
        symbol: str,
        spot_prices: Dict[str, Any]
    ) -> float:
        """
        Gets spot price by token symbol
        from CoinGecko price data.
        """
        for token_id, data in spot_prices.items():
            if data.get("symbol", "").upper() == symbol.upper():
                return float(data.get("price", 0))
        return 0.0

    def _get_spot_price_by_id(
        self,
        coingecko_id: str,
        spot_prices: Dict[str, Any]
    ) -> float:
        """
        Gets spot price by CoinGecko token ID.
        """
        if coingecko_id in spot_prices:
            return float(
                spot_prices[coingecko_id].get("price", 0)
            )
        return 0.0

    def _safe_default(self) -> Dict[str, Any]:
        """
        Safe default when all sources unavailable.
        CONSERVATIVE: major_unlock_imminent = False
        """
        return {
            "major_unlock_imminent": False,
            "upcoming_unlocks": [],
            "entry_window_active": False,
            "entry_opportunities": [],
            "total_upcoming_value": 0.0
        }