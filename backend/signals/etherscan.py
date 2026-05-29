"""
CAYE v3.0 — Signal 4: Etherscan API
DIMENSION: Invisible (35%)
Ethereum gas price acceleration rate.
>300% spike in 5 minutes = insider_activity = True
MEV bot front-running signal.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger
import httpx

from backend.config import get_settings
from backend.signals.cache import cache

settings = get_settings()


class EtherscanSignal:
    """
    Signal 4: Etherscan Gas Oracle API
    Detects MEV bot and insider activity via
    gas price acceleration anomalies.
    300%+ spike in 5 minutes = insider_activity = True
    """

    CACHE_NAMESPACE = "etherscan_gas"
    BASE_URL = "https://api.etherscan.io/api"
    MAX_RETRIES = 3
    ACCELERATION_THRESHOLD = 3.0  # 300%

    async def fetch_gas_data(
        self,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Fetches current gas prices and calculates
        5-minute acceleration rate.

        Returns:
            insider_activity: bool
            acceleration_rate: float
            current_gas_gwei: int
        """
        if not settings.etherscan_api_key:
            logger.warning(
                "Etherscan: no API key configured"
            )
            return self._safe_default()

        # Fetch current gas
        gas_data = await self._fetch_gas()

        if gas_data is None:
            logger.error(
                "Etherscan: API failed, using safe default"
            )
            return self._safe_default()

        current_gas = gas_data["safe_gas"]
        propose_gas = gas_data["propose_gas"]
        fast_gas = gas_data["fast_gas"]

        # Store in DB
        if db_session:
            await self._store_snapshot(
                db_session,
                current_gas,
                propose_gas,
                fast_gas
            )

        # Calculate acceleration from DB
        acceleration_rate = 0.0
        if db_session:
            acceleration_rate = await self._calculate_acceleration(
                db_session, current_gas
            )

        insider_activity = (
            acceleration_rate > self.ACCELERATION_THRESHOLD
        )

        result = {
            "insider_activity": insider_activity,
            "gas_acceleration_rate": acceleration_rate,
            "current_gas_gwei": current_gas,
            "propose_gas_gwei": propose_gas,
            "fast_gas_gwei": fast_gas,
        }

        # Cache for 10 minutes
        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            result,
            settings.cache_ttl_etherscan
        )

        if insider_activity:
            logger.warning(
                f"Etherscan: INSIDER ACTIVITY DETECTED! "
                f"Gas acceleration: {acceleration_rate:.1f}x "
                f"({current_gas} Gwei)"
            )
        else:
            logger.info(
                f"Etherscan: gas={current_gas} Gwei "
                f"acceleration={acceleration_rate:.2f}x "
                f"insider={insider_activity}"
            )

        return result

    async def _fetch_gas(self) -> Optional[Dict]:
        """
        Fetches current gas oracle data from Etherscan.
        """
        params = {
            "module": "gastracker",
            "action": "gasoracle",
            "apikey": settings.etherscan_api_key
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=10.0
                ) as client:
                    response = await client.get(
                        self.BASE_URL, params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("status") != "1":
                        logger.warning(
                            f"Etherscan API error: "
                            f"{data.get('message')}"
                        )
                        return None

                    result = data.get("result", {})
                    return {
                        "safe_gas": int(
                            result.get("SafeGasPrice", 0)
                        ),
                        "propose_gas": int(
                            result.get("ProposeGasPrice", 0)
                        ),
                        "fast_gas": int(
                            result.get("FastGasPrice", 0)
                        ),
                    }

            except Exception as e:
                logger.warning(
                    f"Etherscan error: {e} "
                    f"(attempt {attempt + 1})"
                )

            if attempt < self.MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(1)

        return None

    async def _store_snapshot(
        self,
        db_session,
        gas_price: int,
        propose_gas: int,
        fast_gas: int
    ):
        """
        Stores gas snapshot to DB for
        acceleration calculation.
        """
        try:
            from backend.models import GasSnapshot
            snapshot = GasSnapshot(
                gas_price_gwei=gas_price,
                propose_gas_price=propose_gas,
                fast_gas_price=fast_gas
            )
            db_session.add(snapshot)
            db_session.commit()
        except Exception as e:
            logger.warning(f"Gas snapshot store error: {e}")
            db_session.rollback()

    async def _calculate_acceleration(
        self,
        db_session,
        current_gas: int
    ) -> float:
        """
        Calculates 5-minute gas acceleration rate.
        Returns ratio of current/prior gas price.
        """
        try:
            from backend.models import GasSnapshot
            from sqlalchemy import desc

            cutoff = datetime.utcnow() - timedelta(minutes=5)

            prior = db_session.query(
                GasSnapshot
            ).filter(
                GasSnapshot.recorded_at <= cutoff
            ).order_by(
                desc(GasSnapshot.recorded_at)
            ).first()

            if prior and prior.gas_price_gwei > 0:
                rate = (
                    current_gas - prior.gas_price_gwei
                ) / prior.gas_price_gwei
                return rate
            else:
                logger.info(
                    "Etherscan: no prior gas reading — "
                    "baseline establishing"
                )
                return 0.0

        except Exception as e:
            logger.warning(f"Gas acceleration error: {e}")
            return 0.0

    def _safe_default(self) -> Dict[str, Any]:
        """
        Safe default when Etherscan unavailable.
        CONSERVATIVE: insider_activity = False
        """
        return {
            "insider_activity": False,
            "gas_acceleration_rate": 0.0,
            "current_gas_gwei": 0,
            "propose_gas_gwei": 0,
            "fast_gas_gwei": 0,
        }