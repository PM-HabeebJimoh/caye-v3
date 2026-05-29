"""
CAYE v3.0 — Signal 8: Coinglass API
DIMENSION: Invisible (35%)
Perpetual futures funding rates.
>0.05% per 8h = over_leveraged = True
Identifies unsustainable leveraged longs.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class CoinglassSignal:
    """
    Signal 8: Coinglass Public API
    Monitors BTC, ETH, SOL funding rates.
    funding_rate > 0.0005 = over_leveraged = True
    Fallback: any_over_leveraged = False (conservative)
    """

    CACHE_NAMESPACE = "coinglass_funding"
    BASE_URL = "https://open-api-v3.coinglass.com/api"
    MAX_RETRIES = 3
    FUNDING_THRESHOLD = 0.0005  # 0.05% per 8h
    SYMBOLS = ["BTC", "ETH", "SOL"]

    async def fetch_funding_data(self) -> Dict[str, Any]:
        """
        Fetches current funding rates for BTC, ETH, SOL.

        Returns:
            any_over_leveraged: bool
            funding_rate_details: dict per symbol
        """
        if not settings.coinglass_api_key:
            logger.warning(
                "Coinglass: no API key configured"
            )
            return self._safe_default("NO_KEY")

        # Check cache
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        raw_data = await self._fetch_funding_rates()

        if raw_data is None:
            stale = cache.get_stale(self.CACHE_NAMESPACE)
            if stale:
                logger.warning(
                    "Coinglass: serving stale cache"
                )
                stale["source_flag"] = "STALE_CACHE"
                return stale

            logger.warning(
                "Coinglass: API failed — using safe default"
            )
            return self._safe_default("API_FAILED")

        parsed = self._parse_funding_rates(raw_data)

        any_over_leveraged = any(
            item.get("over_leveraged", False)
            for item in parsed.values()
        )

        result = {
            "any_over_leveraged": any_over_leveraged,
            "funding_rate_details": parsed,
            "source_flag": "LIVE"
        }

        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_coinglass
        )

        if any_over_leveraged:
            flagged = [
                sym for sym, data in parsed.items()
                if data.get("over_leveraged", False)
            ]
            logger.warning(
                f"Coinglass: OVER-LEVERAGED! "
                f"Symbols: {flagged}"
            )
        else:
            logger.info(
                f"Coinglass: funding rates normal "
                f"over_leveraged={any_over_leveraged}"
            )

        return result

    async def _fetch_funding_rates(self) -> Optional[List]:
        """
        Fetches current funding rates from Coinglass.
        """
        url = (
            f"{self.BASE_URL}/futures/funding-rate/current"
        )
        headers = {
            "coinglassSecret": settings.coinglass_api_key
        }
        params = {
            "symbol": ",".join(self.SYMBOLS)
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=15.0
                ) as client:
                    response = await client.get(
                        url,
                        headers=headers,
                        params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("code") == "0":
                        return data.get("data", [])
                    else:
                        logger.warning(
                            f"Coinglass API error: "
                            f"{data.get('msg', 'Unknown')}"
                        )
                        return None

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Coinglass HTTP {e.response.status_code} "
                    f"(attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"Coinglass error: {e} "
                    f"(attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(2)

        return None

    def _parse_funding_rates(
        self,
        raw_data: List
    ) -> Dict[str, Any]:
        """
        Parses Coinglass response into
        per-symbol funding rate objects.
        """
        result = {}

        for item in raw_data:
            symbol = item.get("symbol", "UNKNOWN")

            if symbol not in self.SYMBOLS:
                continue

            try:
                funding_rate = float(
                    item.get("fundingRate", 0) or 0
                )
            except (ValueError, TypeError):
                funding_rate = 0.0

            annualized = funding_rate * 3 * 365
            over_leveraged = (
                funding_rate > self.FUNDING_THRESHOLD
            )

            result[symbol] = {
                "symbol": symbol,
                "funding_rate": funding_rate,
                "funding_rate_pct": funding_rate * 100,
                "annualized_pct": annualized * 100,
                "over_leveraged": over_leveraged,
            }

        # Ensure all symbols present
        for sym in self.SYMBOLS:
            if sym not in result:
                result[sym] = {
                    "symbol": sym,
                    "funding_rate": 0.0,
                    "funding_rate_pct": 0.0,
                    "annualized_pct": 0.0,
                    "over_leveraged": False,
                }

        return result

    def _safe_default(
        self,
        reason: str = "UNAVAILABLE"
    ) -> Dict[str, Any]:
        """
        Safe default when Coinglass unavailable.
        CONSERVATIVE: any_over_leveraged = False
        Source flagged so dashboard shows fallback.
        """
        return {
            "any_over_leveraged": False,
            "funding_rate_details": {
                sym: {
                    "symbol": sym,
                    "funding_rate": 0.0,
                    "funding_rate_pct": 0.0,
                    "annualized_pct": 0.0,
                    "over_leveraged": False
                }
                for sym in self.SYMBOLS
            },
            "source_flag": f"FALLBACK_{reason}"
        }