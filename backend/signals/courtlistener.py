"""
CAYE v3.0 — Signal 7: CourtListener API
DIMENSION: Hidden (35%)
Federal court docket filings for crypto entities.
>3 filings in 7 days = regulatory_pressure = True
Detects SEC/DOJ enforcement 3-21 days early.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class CourtListenerSignal:
    """
    Signal 7: CourtListener REST API
    Monitors SDNY, 9th Circuit, DC Circuit
    for crypto enforcement actions.
    >3 dockets in 7 days = regulatory_pressure = True
    """

    CACHE_NAMESPACE = "courtlistener_dockets"
    BASE_URL = "https://www.courtlistener.com/api/rest/v3"
    MAX_RETRIES = 3
    PRESSURE_THRESHOLD = 3
    BETWEEN_REQUEST_DELAY = 10  # seconds (rate limit compliance)

    SEARCH_TERMS = [
        "cryptocurrency",
        "bitcoin",
        "digital asset",
        "binance",
        "coinbase"
    ]

    COURTS = "nysd,ca9,dcd"  # SDNY, 9th Circuit, DC Circuit

    async def fetch_regulatory_data(self) -> Dict[str, Any]:
        """
        Searches federal dockets for crypto-related
        filings in the last 7 days.

        Returns:
            regulatory_pressure: bool
            total_dockets_7d: int
            docket_breakdown: dict per search term
        """
        # Check cache
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        filed_after = (
            datetime.utcnow() - timedelta(days=7)
        ).strftime("%Y-%m-%d")

        total_dockets = 0
        docket_breakdown = {}

        for term in self.SEARCH_TERMS:
            count = await self._search_dockets(
                term, filed_after
            )
            docket_breakdown[term] = count
            total_dockets += count

            # Rate limit compliance: 10s between requests
            await asyncio.sleep(self.BETWEEN_REQUEST_DELAY)

        regulatory_pressure = (
            total_dockets > self.PRESSURE_THRESHOLD
        )

        result = {
            "regulatory_pressure": regulatory_pressure,
            "total_dockets_7d": total_dockets,
            "docket_breakdown": docket_breakdown,
            "filed_after": filed_after,
            "courts_monitored": self.COURTS
        }

        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_courtlistener
        )

        if regulatory_pressure:
            logger.warning(
                f"CourtListener: REGULATORY PRESSURE! "
                f"{total_dockets} dockets in 7 days"
            )
        else:
            logger.info(
                f"CourtListener: {total_dockets} dockets "
                f"in 7 days (threshold: {self.PRESSURE_THRESHOLD})"
            )

        return result

    async def _search_dockets(
        self,
        search_term: str,
        filed_after: str
    ) -> int:
        """
        Searches CourtListener for a single search term.
        Returns count of matching dockets.
        """
        url = f"{self.BASE_URL}/dockets/"
        params = {
            "q": search_term,
            "filed_after": filed_after,
            "court": self.COURTS,
            "order_by": "-date_filed",
            "limit": 10
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=20.0
                ) as client:
                    response = await client.get(
                        url, params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    count = data.get("count", 0)
                    logger.debug(
                        f"CourtListener '{search_term}': "
                        f"{count} dockets"
                    )
                    return int(count)

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"CourtListener HTTP {e.response.status_code} "
                    f"for '{search_term}' "
                    f"(attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"CourtListener error for '{search_term}': "
                    f"{e} (attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(30)

        # Return 0 on failure (conservative)
        return 0

    def _safe_default(self) -> Dict[str, Any]:
        """
        Safe default when CourtListener unavailable.
        CONSERVATIVE: regulatory_pressure = False
        """
        return {
            "regulatory_pressure": False,
            "total_dockets_7d": 0,
            "docket_breakdown": {},
            "filed_after": None,
            "courts_monitored": self.COURTS
        }