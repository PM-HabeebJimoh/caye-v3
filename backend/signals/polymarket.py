"""
CAYE v3.0 — Signal 1: Polymarket Gamma API
DIMENSION: Visible (15%)
Fetches all active crypto markets with prices,
liquidity, volume, and resolution dates.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
import httpx

from backend.config import get_settings, CRYPTO_INCLUDE_KEYWORDS, CRYPTO_EXCLUDE_KEYWORDS, SUBCATEGORY_KEYWORDS
from backend.signals.cache import cache

settings = get_settings()

# ─────────────────────────────────────────
# CRYPTO FILTER FUNCTIONS
# 6-layer enforcement starts here (Layer 2)
# ─────────────────────────────────────────

def is_crypto_market(question: str) -> bool:
    """
    Layer 2 of 6-layer crypto enforcement.
    Returns True only if market is crypto AND
    does not contain any exclusion keywords.
    """
    question_lower = question.lower()

    include_found = any(
        keyword in question_lower
        for keyword in CRYPTO_INCLUDE_KEYWORDS
    )

    exclude_found = any(
        keyword in question_lower
        for keyword in CRYPTO_EXCLUDE_KEYWORDS
    )

    return include_found and not exclude_found


def classify_subcategory(question: str) -> str:
    """
    Classifies a crypto market question into
    one of 9 subcategories for engine routing.
    """
    question_lower = question.lower()

    for subcategory, keywords in SUBCATEGORY_KEYWORDS.items():
        if any(kw in question_lower for kw in keywords):
            return subcategory

    return "GENERAL_CRYPTO"


def extract_price_target(question: str) -> Optional[float]:
    """
    Extracts numeric price target from market question.
    Example: "Will BTC hit $150,000?" → 150000.0
    """
    patterns = [
        r'\$([0-9,]+(?:\.[0-9]+)?)[kK]?',
        r'([0-9,]+(?:\.[0-9]+)?)\s*(?:USD|USDT|dollars?)',
        r'(?:reach|hit|exceed|above|below|drop|fall)\s+\$?([0-9,]+(?:\.[0-9]+)?)',
    ]

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(',', '')
            try:
                value = float(value_str)
                if question.lower().find('k') != -1:
                    value *= 1000
                return value
            except ValueError:
                continue

    return None


def extract_token_symbol(question: str) -> Optional[str]:
    """
    Extracts token symbol from market question.
    Returns uppercase token symbol or None.
    """
    token_patterns = {
        'BTC': ['bitcoin', 'btc'],
        'ETH': ['ethereum', 'eth'],
        'SOL': ['solana', 'sol'],
        'BNB': ['binance', 'bnb'],
        'ARB': ['arbitrum', 'arb'],
        'OP': ['optimism', ' op '],
        'APT': ['aptos', 'apt'],
        'DOGE': ['dogecoin', 'doge'],
        'XRP': ['ripple', 'xrp'],
        'ADA': ['cardano', 'ada'],
        'AVAX': ['avalanche', 'avax'],
        'LINK': ['chainlink', 'link'],
        'UNI': ['uniswap', 'uni'],
        'MATIC': ['polygon', 'matic'],
        'PEPE': ['pepe'],
        'SHIB': ['shiba', 'shib'],
        'USDT': ['tether', 'usdt'],
        'USDC': ['usdc', 'circle'],
    }

    question_lower = question.lower()
    for symbol, patterns in token_patterns.items():
        if any(p in question_lower for p in patterns):
            return symbol

    return None


# ─────────────────────────────────────────
# POLYMARKET SIGNAL CLASS
# ─────────────────────────────────────────

class PolymarketSignal:
    """
    Signal 1: Polymarket Gamma API
    Fetches and filters all active crypto markets.
    """

    CACHE_NAMESPACE = "polymarket_markets"
    BASE_URL = "https://gamma-api.polymarket.com"
    MAX_RETRIES = 3
    RETRY_DELAYS = [2, 4, 8]

    async def fetch_all_markets(self) -> List[Dict[str, Any]]:
        """
        Fetches all active crypto markets from Polymarket.
        Applies crypto filter (Layer 2).
        Returns list of parsed market objects.
        """
        # Check cache first
        cached = cache.get(self.CACHE_NAMESPACE)
        if cached is not None:
            logger.debug(
                f"Polymarket cache hit: "
                f"{len(cached)} markets"
            )
            return cached

        # Fetch fresh data
        all_markets = []
        offset = 0
        page_size = 100

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                markets_page = await self._fetch_page(
                    client, offset, page_size
                )

                if markets_page is None:
                    # API failed — try stale cache
                    stale = cache.get_stale(self.CACHE_NAMESPACE)
                    if stale:
                        logger.warning(
                            "Polymarket API failed — "
                            "serving stale cache"
                        )
                        return stale
                    logger.error(
                        "Polymarket API failed — "
                        "no cache available"
                    )
                    return []

                all_markets.extend(markets_page)

                if len(markets_page) < page_size:
                    break

                offset += page_size

        # Parse and filter
        parsed = []
        for market in all_markets:
            parsed_market = self._parse_market(market)
            if parsed_market:
                parsed.append(parsed_market)

        # Store in cache
        cache.set_with_stale(
            self.CACHE_NAMESPACE,
            parsed,
            settings.cache_ttl_polymarket
        )

        logger.info(
            f"Polymarket: fetched {len(all_markets)} markets, "
            f"{len(parsed)} passed crypto filter"
        )

        return parsed

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        offset: int,
        limit: int
    ) -> Optional[List[Dict]]:
        """
        Fetches a single page of markets with retry logic.
        """
        url = f"{self.BASE_URL}/markets"
        params = {
            "closed": "false",
            "tag": "crypto",
            "limit": limit,
            "offset": offset
        }

        for attempt, delay in enumerate(self.RETRY_DELAYS, 1):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Polymarket HTTP {e.response.status_code} "
                    f"(attempt {attempt}/{self.MAX_RETRIES})"
                )
            except httpx.TimeoutException:
                logger.warning(
                    f"Polymarket timeout "
                    f"(attempt {attempt}/{self.MAX_RETRIES})"
                )
            except Exception as e:
                logger.warning(
                    f"Polymarket error: {e} "
                    f"(attempt {attempt}/{self.MAX_RETRIES})"
                )

            if attempt < self.MAX_RETRIES:
                import asyncio
                await asyncio.sleep(delay)

        return None

    def _parse_market(
        self,
        raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parses raw Polymarket API response into
        standardized market object.
        Returns None if market fails crypto filter.
        """
        try:
            question = raw.get("question", "")

            # Layer 2: Crypto filter
            if not is_crypto_market(question):
                return None

            # Extract prices
            outcome_prices = raw.get("outcomePrices", ["0.5", "0.5"])
            if isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
                yes_price = float(outcome_prices[0])
                no_price = float(outcome_prices[1])
            else:
                yes_price = 0.5
                no_price = 0.5

            # Extract tokens
            tokens = raw.get("tokens", [])
            yes_token_id = None
            no_token_id = None
            for token in tokens:
                if token.get("outcome", "").upper() == "YES":
                    yes_token_id = token.get("token_id")
                elif token.get("outcome", "").upper() == "NO":
                    no_token_id = token.get("token_id")

            # Build Polymarket URL
            slug = raw.get("slug", "")
            polymarket_url = (
                f"https://polymarket.com/event/{slug}"
                if slug else None
            )

            # Parse end date
            end_date_str = raw.get("endDateIso", raw.get("end_date_iso"))
            end_date = None
            days_to_expiry = None
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(
                        end_date_str.replace('Z', '+00:00')
                    )
                    now = datetime.now(end_date.tzinfo)
                    days_to_expiry = (end_date - now).days
                except Exception:
                    pass

            # Classify subcategory
            subcategory = classify_subcategory(question)

            # Extract token and price target
            token_symbol = extract_token_symbol(question)
            price_target = extract_price_target(question)

            return {
                "market_id": raw.get("conditionId", raw.get("condition_id", "")),
                "condition_id": raw.get("conditionId", raw.get("condition_id")),
                "question": question,
                "polymarket_url": polymarket_url,
                "slug": slug,
                "market_category": "CRYPTO",
                "subcategory": subcategory,
                "yes_price": yes_price,
                "no_price": no_price,
                "liquidity": float(raw.get("liquidity", 0) or 0),
                "volume": float(raw.get("volume", 0) or 0),
                "end_date": end_date.isoformat() if end_date else None,
                "days_to_expiry": days_to_expiry,
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "token_symbol": token_symbol,
                "price_target": price_target,
                "spread": abs(yes_price + no_price - 1.0),
            }

        except Exception as e:
            logger.warning(f"Market parse error: {e}")
            return None