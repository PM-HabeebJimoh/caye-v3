"""
CAYE v3.0 — Application Configuration
Loads all environment variables and system settings.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):

    # ─────────────────────────────────────────
    # APPLICATION
    # ─────────────────────────────────────────
    app_env: str = Field(default="production", env="APP_ENV")
    app_debug: bool = Field(default=False, env="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    secret_key: str = Field(default="changeme", env="SECRET_KEY")

    # ─────────────────────────────────────────
    # DATABASE
    # ─────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://caye_user:caye_pass@postgres:5432/caye_db",
        env="DATABASE_URL"
    )
    postgres_db: str = Field(default="caye_db", env="POSTGRES_DB")
    postgres_user: str = Field(default="caye_user", env="POSTGRES_USER")
    postgres_password: str = Field(default="caye_pass", env="POSTGRES_PASSWORD")

    # ─────────────────────────────────────────
    # REDIS
    # ─────────────────────────────────────────
    redis_url: str = Field(
        default="redis://redis:6379/0",
        env="REDIS_URL"
    )
    celery_broker_url: str = Field(
        default="redis://redis:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://redis:6379/0",
        env="CELERY_RESULT_BACKEND"
    )

    # ─────────────────────────────────────────
    # API KEYS
    # ─────────────────────────────────────────
    etherscan_api_key: str = Field(
        default="",
        env="ETHERSCAN_API_KEY"
    )
    fred_api_key: str = Field(
        default="",
        env="FRED_API_KEY"
    )
    github_token: str = Field(
        default="",
        env="GITHUB_TOKEN"
    )
    coinglass_api_key: str = Field(
        default="",
        env="COINGLASS_API_KEY"
    )

    # ─────────────────────────────────────────
    # SYSTEM SETTINGS (Mathematical Gates)
    # ─────────────────────────────────────────
    default_bankroll: float = Field(
        default=10000.0,
        env="DEFAULT_BANKROLL"
    )
    min_trade_size: float = Field(
        default=50.0,
        env="MIN_TRADE_SIZE"
    )
    max_kelly_fraction: float = Field(
        default=0.25,
        env="MAX_KELLY_FRACTION"
    )
    cis_threshold: float = Field(
        default=0.89,
        env="CIS_THRESHOLD"
    )
    price_ceiling: float = Field(
        default=0.52,
        env="PRICE_CEILING"
    )
    min_liquidity: float = Field(
        default=50000.0,
        env="MIN_LIQUIDITY"
    )
    min_days_to_expiry: int = Field(
        default=2,
        env="MIN_DAYS_TO_EXPIRY"
    )

    # ─────────────────────────────────────────
    # SCAN INTERVALS (seconds)
    # ─────────────────────────────────────────
    scan_markets_interval: int = Field(
        default=60,
        env="SCAN_MARKETS_INTERVAL"
    )
    fast_signals_interval: int = Field(
        default=300,
        env="FAST_SIGNALS_INTERVAL"
    )
    medium_signals_interval: int = Field(
        default=1800,
        env="MEDIUM_SIGNALS_INTERVAL"
    )
    slow_signals_interval: int = Field(
        default=21600,
        env="SLOW_SIGNALS_INTERVAL"
    )
    cleanup_interval: int = Field(
        default=3600,
        env="CLEANUP_INTERVAL"
    )

    # ─────────────────────────────────────────
    # EXTERNAL API URLS
    # ─────────────────────────────────────────
    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    coingecko_url: str = "https://api.coingecko.com/api/v3"
    defillama_url: str = "https://api.llama.fi"
    etherscan_url: str = "https://api.etherscan.io/api"
    fred_url: str = "https://api.stlouisfed.org/fred/series/observations"
    github_url: str = "https://api.github.com"
    courtlistener_url: str = "https://www.courtlistener.com/api/rest/v3"
    coinglass_url: str = "https://open-api-v3.coinglass.com/api"
    tokenunlocks_url: str = "https://token.unlocks.app/api/vesting"

    # ─────────────────────────────────────────
    # CACHE TTL (seconds)
    # ─────────────────────────────────────────
    cache_ttl_polymarket: int = 300
    cache_ttl_coingecko: int = 300
    cache_ttl_defillama: int = 1800
    cache_ttl_etherscan: int = 600
    cache_ttl_fred: int = 21600
    cache_ttl_github: int = 21600
    cache_ttl_courtlistener: int = 21600
    cache_ttl_coinglass: int = 1800
    cache_ttl_tokenunlocks: int = 43200

    # ─────────────────────────────────────────
    # GITHUB REPOSITORIES TO MONITOR
    # ─────────────────────────────────────────
    github_repos: list = [
        "ethereum/go-ethereum",
        "solana-labs/solana",
        "bnb-chain/bsc",
        "OffchainLabs/arbitrum",
        "ethereum-optimism/optimism",
        "aptos-labs/aptos-core"
    ]

    # ─────────────────────────────────────────
    # COINGECKO TOKEN IDS
    # ─────────────────────────────────────────
    coingecko_token_ids: list = [
        "bitcoin", "ethereum", "solana", "binancecoin",
        "arbitrum", "optimism", "aptos", "dogecoin",
        "ripple", "cardano", "avalanche-2", "chainlink",
        "uniswap", "aave", "maker", "compound",
        "polygon", "near", "cosmos", "the-open-network", "sui"
    ]

    # ─────────────────────────────────────────
    # DETERMINISTIC TOKEN UNLOCK SCHEDULE
    # Smart contract verified dates
    # ─────────────────────────────────────────
    token_unlock_schedule: dict = {
        "APT": {
            "unlock_day": 12,
            "unlock_amount": 11300000,
            "coingecko_id": "aptos"
        },
        "ARB": {
            "unlock_day": 16,
            "unlock_amount": 92650000,
            "coingecko_id": "arbitrum"
        }
    }

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    Use this everywhere to avoid re-reading .env on each call.
    """
    return Settings()


# ─────────────────────────────────────────
# CRYPTO FILTER KEYWORDS
# Used by is_crypto_market() in all modules
# ─────────────────────────────────────────

CRYPTO_INCLUDE_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "defi",
    "solana", "sol", "binance", "bnb", "coinbase", "usdt",
    "usdc", "stablecoin", "depeg", "altcoin", "token",
    "blockchain", "web3", "doge", "dogecoin", "xrp", "ripple",
    "cardano", "ada", "polygon", "matic", "avalanche", "avax",
    "chainlink", "link", "uniswap", "uni", "aave", "compound",
    "maker", "dao", "nft", "dex", "cex", "exchange", "wallet",
    "halving", "mining", "miner", "arbitrum", "arb", "optimism",
    "op", "aptos", "apt", "sui", "pepe", "shib", "shiba",
    "memecoin", "liquidation", "funding rate", "tether", "circle",
    "ftx", "alameda", "grayscale", "gbtc", "blackrock crypto",
    "fidelity crypto", "cz", "terra", "luna", "celsius crypto",
    "blockfi", "genesis crypto", "layer 2", "l2", "rollup",
    "smart contract", "protocol", "tvl", "proof of stake",
    "proof of work", "validator", "on-chain", "crypto etf",
    "btc etf", "eth etf", "sec crypto", "cftc crypto",
    "digital asset"
]

CRYPTO_EXCLUDE_KEYWORDS = [
    "election", "president", "congress", "senate",
    "republican", "democrat", "super bowl", "nba", "nfl",
    "nhl", "mlb", "championship", "mvp", "oscar", "grammy",
    "hurricane", "earthquake", "temperature", "rainfall",
    "snow", "ukraine war", "russia war", "israel", "gaza",
    "nato", "fda drug", "vaccine", "clinical trial",
    "spacex launch", "tesla stock", "fed rate hike",
    "us gdp", "us unemployment", "us inflation cpi",
    "uk prime minister", "french election", "german election"
]

SUBCATEGORY_KEYWORDS = {
    "EXCHANGE_SOLVENCY": [
        "halt", "bankrupt", "insolvency", "withdrawal", "ftx", "celsius"
    ],
    "ETF_REGULATORY": [
        "etf", "sec approval", "grayscale", "gbtc", "blackrock etf"
    ],
    "STABLECOIN_DEPEG": [
        "depeg", "usdt", "usdc", "tether", "circle", "peg", "dai"
    ],
    "TOKEN_UNLOCK": [
        "arbitrum", "arb", "optimism", "op", "aptos", "apt",
        "unlock", "vesting"
    ],
    "PRICE_MILESTONE_BULL": [
        "reach", "hit", "exceed", "above", "ath", "all time high"
    ],
    "PRICE_MILESTONE_BEAR": [
        "below", "drop", "fall", "crash", "collapse"
    ],
    "PROTOCOL_HACK": [
        "hack", "exploit", "drain", "rug", "bridge attack", "protocol"
    ],
    "FOUNDER_ACTION": [
        "cz", "resign", "arrested", "indicted", "founder", "step down"
    ]
}