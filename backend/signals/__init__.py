"""
CAYE v3.0 — Signal Collectors Package
9 live data signals across 4 dimensions.

DIMENSION 1 VISIBLE   (15%): Polymarket, CoinGecko
DIMENSION 2 INVISIBLE (35%): DefiLlama, Etherscan, Coinglass
DIMENSION 3 HIDDEN    (35%): GitHub, CourtListener, TokenUnlocks
DIMENSION 4 SCATTERED (15%): FRED
"""

from backend.signals.polymarket import PolymarketSignal
from backend.signals.coingecko import CoinGeckoSignal
from backend.signals.defillama import DefiLlamaSignal
from backend.signals.etherscan import EtherscanSignal
from backend.signals.fred import FREDSignal
from backend.signals.github import GitHubSignal
from backend.signals.courtlistener import CourtListenerSignal
from backend.signals.coinglass import CoinglassSignal
from backend.signals.tokenunlocks import TokenUnlocksSignal

__all__ = [
    "PolymarketSignal",
    "CoinGeckoSignal",
    "DefiLlamaSignal",
    "EtherscanSignal",
    "FREDSignal",
    "GitHubSignal",
    "CourtListenerSignal",
    "CoinglassSignal",
    "TokenUnlocksSignal",
]