"""
CAYE v3.0 — Signal 3: DefiLlama API
DIMENSION: Invisible (35%)
Stablecoin market cap flows.
Detects capital exodus from crypto ecosystem.
Threshold: -$500M in 48 hours = stablecoin_exodus = True
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class DefiLlamaSignal:
    """
    Signal 3: DefiLlama Stablecoins API
    Monitors USDT + USDC market cap flows.
    -$500M+ in 48h triggers stablecoin_exodus = True
    """

    CACHE_NAMESPACE = "defillama_stablecoins"
    BASE_URL = "https://api.llama.fi"
    MAX_RETRIES = 3
    EXODUS_THRESHOLD = -500_000_000  # -$500M

    async def fetch_stablecoin_data(
        self,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Fetches current stablecoin market caps
        and calculates 48h delta.

        Returns:
            stablecoin_exodus: bool
            delta_48h: float
            total_mcap: float
            usdt_mcap: float
            usdc_mcap: float
        """
        # Check cache
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            return cached

        # Fetch from API
        raw_data = await self._fetch_raw()

        if raw_data is None:
            # API failed
            stale = cache.get_stale(self.CACHE_NAMESPACE)
            if stale:
                logger.warning("DefiLlama: serving stale cache")
                return stale

            # Safe default
            logger.error("DefiLlama: API failed, using safe default")
            return self._safe_default()

        # Parse USDT + USDC
        usdt_mcap, usdc_mcap = self._extract_mcaps(raw_data)
        total_mcap = usdt_mcap + usdc_mcap

        # Store snapshot in DB if session provided
        if db_session:
            await self._store_snapshot(
                db_session, usdt_mcap, usdc_mcap, total_mcap
            )

        # Calculate 48h delta from DB
        delta_48h = 0.0
        if db_session:
            delta_48h = await self._calculate_delta(
                db_session, total_mcap
            )

        stablecoin_exodus = delta_48h < self.EXODUS_THRESHOLD

        result = {
            "stablecoin_exodus": stablecoin_exodus,
            "stablecoin_delta_48h": delta_48h,
            "total_stablecoin_mcap": total_mcap,
            "usdt_mcap": usdt_mcap,
            "usdc_mcap": usdc_mcap,
        }

        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_defillama
        )

        logger.info(
            f"DefiLlama: USDT={usdt_mcap/1e9:.1f}B "
            f"USDC={usdc_mcap/1e9:.1f}B "
            f"Total={total_mcap/1e9:.1f}B "
            f"Delta48h={delta_48h/1e9:.2f}B "
            f"Exodus={stablecoin_exodus}"
        )

        return result

    async def _fetch_raw(self) -> Optional[Dict]:
        """
        Fetches raw stablecoin data from DefiLlama.
        """
        url = f"{self.BASE_URL}/stablecoins"
        params = {"includePrices": "true"}

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=20.0
                ) as client:
                    response = await client.get(
                        url, params=params
                    )
                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"DefiLlama HTTP {e.response.status_code} "
                    f"(attempt {attempt + 1})"
                )
            except Exception as e:
                logger.warning(
                    f"DefiLlama error: {e} "
                    f"(attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(2)

        return None

    def _extract_mcaps(
        self,
        raw: Dict
    ) -> Tuple[float, float]:
        """
        Extracts USDT and USDC market caps
        from DefiLlama response.
        """
        usdt_mcap = 0.0
        usdc_mcap = 0.0

        pegged_assets = raw.get("peggedAssets", [])

        for asset in pegged_assets:
            symbol = asset.get("symbol", "").upper()
            circulating = asset.get("circulating", {})
            mcap = float(circulating.get("usd", 0) or 0)

            if symbol == "USDT":
                usdt_mcap = mcap
            elif symbol == "USDC":
                usdc_mcap = mcap

        return usdt_mcap, usdc_mcap

    async def _store_snapshot(
        self,
        db_session,
        usdt_mcap: float,
        usdc_mcap: float,
        total_mcap: float
    ):
        """
        Stores current stablecoin snapshot to DB
        for delta calculation.
        """
        try:
            from backend.models import StablecoinSnapshot
            snapshot = StablecoinSnapshot(
                usdt_mcap=usdt_mcap,
                usdc_mcap=usdc_mcap,
                total_mcap=total_mcap
            )
            db_session.add(snapshot)
            db_session.commit()
        except Exception as e:
            logger.warning(f"DefiLlama snapshot store error: {e}")
            db_session.rollback()

    async def _calculate_delta(
        self,
        db_session,
        current_total: float
    ) -> float:
        """
        Calculates 48-hour delta by comparing
        current total to prior 48h snapshot.
        """
        try:
            from backend.models import StablecoinSnapshot
            from sqlalchemy import desc

            cutoff = datetime.utcnow() - timedelta(hours=48)

            prior = db_session.query(
                StablecoinSnapshot
            ).filter(
                StablecoinSnapshot.recorded_at <= cutoff
            ).order_by(
                desc(StablecoinSnapshot.recorded_at)
            ).first()

            if prior:
                return current_total - prior.total_mcap
            else:
                logger.info(
                    "DefiLlama: insufficient history "
                    "for 48h delta"
                )
                return 0.0

        except Exception as e:
            logger.warning(f"DefiLlama delta calc error: {e}")
            return 0.0

    def _safe_default(self) -> Dict[str, Any]:
        """
        Returns safe default when API is unavailable.
        CONSERVATIVE: stablecoin_exodus = False
        Never assume True without real data.
        """
        return {
            "stablecoin_exodus": False,
            "stablecoin_delta_48h": 0.0,
            "total_stablecoin_mcap": 0.0,
            "usdt_mcap": 0.0,
            "usdc_mcap": 0.0,
        }