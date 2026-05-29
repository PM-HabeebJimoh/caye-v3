"""
CAYE v3.0 — Signal 5: FRED API
DIMENSION: Scattered (15%)
Federal Reserve Net Macro Liquidity.
Formula: Fed Balance Sheet - RRP - TGA
< -2% weekly = macro_draining = True
Creates invisible ceiling on crypto prices.
"""

from typing import Dict, Any, Optional, Tuple
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class FREDSignal:
    """
    Signal 5: Federal Reserve FRED API
    Calculates net macro liquidity from 3 series:
    WALCL (Fed Balance Sheet)
    RRPONTSYD (Reverse Repo)
    WTREGEN (Treasury General Account)
    """

    CACHE_NAMESPACE = "fred_macro"
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
    MAX_RETRIES = 3
    DRAIN_THRESHOLD = -0.02  # -2% per week

    SERIES = {
        "WALCL": "fed_balance_sheet",
        "RRPONTSYD": "reverse_repo",
        "WTREGEN": "treasury_general_account"
    }

    async def fetch_macro_data(self) -> Dict[str, Any]:
        """
        Fetches all 3 FRED series and calculates
        net macro liquidity and weekly delta.

        Returns:
            macro_draining: bool
            weekly_delta_pct: float
            current_net_liquidity: float
        """
        if not settings.fred_api_key:
            logger.warning("FRED: no API key configured")
            return self._safe_default()

        # Check cache
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        # Fetch all 3 series
        series_data = {}
        for series_id in self.SERIES.keys():
            data = await self._fetch_series(series_id)
            if data is None:
                logger.error(
                    f"FRED: failed to fetch {series_id}"
                )
                return self._safe_default()
            series_data[series_id] = data

        # Calculate net liquidity
        result = self._calculate_net_liquidity(series_data)

        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_fred
        )

        logger.info(
            f"FRED: net_liquidity="
            f"${result['current_net_liquidity']/1e12:.2f}T "
            f"delta={result['weekly_delta_pct']*100:.2f}% "
            f"draining={result['macro_draining']}"
        )

        return result

    async def _fetch_series(
        self,
        series_id: str
    ) -> Optional[Tuple[float, float]]:
        """
        Fetches latest 2 observations for a FRED series.
        Returns (current_value, prior_value) in millions USD.
        """
        params = {
            "series_id": series_id,
            "api_key": settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 2
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=15.0
                ) as client:
                    response = await client.get(
                        self.BASE_URL, params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    observations = data.get("observations", [])

                    if len(observations) < 2:
                        logger.warning(
                            f"FRED {series_id}: "
                            f"insufficient observations"
                        )
                        return None

                    # Convert millions to dollars
                    def safe_float(val):
                        try:
                            return float(val) * 1_000_000
                        except (ValueError, TypeError):
                            return 0.0

                    current = safe_float(
                        observations[0].get("value", "0")
                    )
                    prior = safe_float(
                        observations[1].get("value", "0")
                    )

                    return (current, prior)

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"FRED {series_id} HTTP "
                    f"{e.response.status_code} "
                    f"(attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"FRED {series_id} error: {e} "
                    f"(attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(5)

        return None

    def _calculate_net_liquidity(
        self,
        series_data: Dict
    ) -> Dict[str, Any]:
        """
        Calculates net macro liquidity:
        Net = Fed_BS - RRP - TGA
        """
        try:
            walcl_curr, walcl_prior = series_data["WALCL"]
            rrp_curr, rrp_prior = series_data["RRPONTSYD"]
            tga_curr, tga_prior = series_data["WTREGEN"]

            current_net = walcl_curr - rrp_curr - tga_curr
            prior_net = walcl_prior - rrp_prior - tga_prior

            if prior_net != 0:
                weekly_delta_pct = (
                    current_net - prior_net
                ) / abs(prior_net)
            else:
                weekly_delta_pct = 0.0

            macro_draining = (
                weekly_delta_pct < self.DRAIN_THRESHOLD
            )

            return {
                "macro_draining": macro_draining,
                "weekly_delta_pct": weekly_delta_pct,
                "current_net_liquidity": current_net,
                "prior_net_liquidity": prior_net,
                "current_fed_bs": walcl_curr,
                "current_rrp": rrp_curr,
                "current_tga": tga_curr,
            }

        except Exception as e:
            logger.error(f"FRED calculation error: {e}")
            return self._safe_default()

    def _safe_default(self) -> Dict[str, Any]:
        """
        Safe default when FRED unavailable.
        CONSERVATIVE: macro_draining = False
        """
        return {
            "macro_draining": False,
            "weekly_delta_pct": 0.0,
            "current_net_liquidity": 0.0,
            "prior_net_liquidity": 0.0,
            "current_fed_bs": 0.0,
            "current_rrp": 0.0,
            "current_tga": 0.0,
        }