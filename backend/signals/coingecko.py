"""
CAYE v3.0 — Signal 2: CoinGecko API
DIMENSION: Visible (15%)
Real-time spot prices for all major
crypto tokens. Used for price target
validation in Engines 3 and 4.
"""

from typing import Dict, Any, Optional
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class CoinGeckoSignal:
    """
    Signal 2: CoinGecko Public API
    Fetches live spot prices for 21 tokens.
    No API key required.
    """

    CACHE_NAMESPACE = "coingecko_prices"
    BASE_URL = "https://api.coingecko.com/api/v3"
    MAX_RETRIES = 3

    async def fetch_spot_prices(self) -> Dict[str, Any]:
        """
        Fetches current spot prices for all
        monitored tokens.
        Returns dict: {token_id: {price, change_24h, momentum}}
        """
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        ids_param = ",".join(settings.coingecko_token_ids)

        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": ids_param,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true"
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=15.0
                ) as client:
                    response = await client.get(
                        url, params=params
                    )

                    # Handle rate limiting
                    if response.status_code == 429:
                        logger.warning(
                            "CoinGecko rate limited — "
                            "waiting 60s"
                        )
                        import asyncio
                        await asyncio.sleep(60)
                        continue

                    response.raise_for_status()
                    raw_data = response.json()

                    parsed = self._parse_prices(raw_data)

                    cache.set_with_stale(
                        self.CACHE_NAMESPACE,
                        parsed,
                        settings.cache_ttl_coingecko
                    )

                    logger.info(
                        f"CoinGecko: fetched prices "
                        f"for {len(parsed)} tokens"
                    )
                    return parsed

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"CoinGecko HTTP {e.response.status_code} "
                    f"(attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"CoinGecko error: {e} "
                    f"(attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(1)

        # Return stale cache or empty
        stale = cache.get_stale(self.CACHE_NAMESPACE)
        if stale:
            logger.warning("CoinGecko: serving stale cache")
            return stale

        logger.error("CoinGecko: no data available")
        return {}

    def _parse_prices(
        self,
        raw: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parses CoinGecko response into
        standardized price objects.
        """
        result = {}

        # Symbol mappings for easy lookup
        symbol_map = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "binancecoin": "BNB",
            "arbitrum": "ARB",
            "optimism": "OP",
            "aptos": "APT",
            "dogecoin": "DOGE",
            "ripple": "XRP",
            "cardano": "ADA",
            "avalanche-2": "AVAX",
            "chainlink": "LINK",
            "uniswap": "UNI",
            "aave": "AAVE",
            "maker": "MKR",
            "compound": "COMP",
            "polygon": "MATIC",
            "near": "NEAR",
            "cosmos": "ATOM",
            "the-open-network": "TON",
            "sui": "SUI"
        }

        for token_id, data in raw.items():
            if not isinstance(data, dict):
                continue

            price = data.get("usd", 0)
            change_24h = data.get("usd_24h_change", 0)
            market_cap = data.get("usd_market_cap", 0)

            result[token_id] = {
                "token_id": token_id,
                "symbol": symbol_map.get(token_id, token_id.upper()),
                "price": float(price) if price else 0.0,
                "change_24h": float(change_24h) if change_24h else 0.0,
                "market_cap": float(market_cap) if market_cap else 0.0,
                "momentum": "BULLISH" if (change_24h or 0) > 0 else "BEARISH"
            }

        return result

    def get_price_by_symbol(
        self,
        symbol: str,
        prices: Dict[str, Any]
    ) -> Optional[float]:
        """
        Looks up current price by token symbol.
        Example: get_price_by_symbol('ARB', prices)
        """
        symbol_upper = symbol.upper()

        for token_id, data in prices.items():
            if data.get("symbol") == symbol_upper:
                return data.get("price")

        return None