"""
CAYE v3.0 — Celery Beat Schedule
All task intervals exactly per specification.

Task 1: scan_markets      → Every 60 seconds
Task 2: fast_signals      → Every 5 minutes
Task 3: medium_signals    → Every 30 minutes
Task 4: slow_signals      → Every 6 hours
Task 5: cleanup_expired   → Every 1 hour
"""

from celery.schedules import crontab
from backend.config import get_settings

settings = get_settings()

BEAT_SCHEDULE = {

    # ─────────────────────────────────────────
    # TASK 1: MARKET SCANNER
    # Highest priority — runs every 60 seconds
    # Scans all Polymarket crypto markets
    # Applies engines + gates + CIS
    # ─────────────────────────────────────────
    "scan-markets-every-60s": {
        "task": "backend.tasks.scan_markets.scan_markets",
        "schedule": settings.scan_markets_interval,  # 60 seconds
        "options": {
            "queue": "scan",
            "expires": 55,  # Expire if not picked up in 55s
        },
    },

    # ─────────────────────────────────────────
    # TASK 2: FAST SIGNALS
    # Runs every 5 minutes
    # Updates: Etherscan gas + CoinGecko prices
    # ─────────────────────────────────────────
    "fast-signals-every-5min": {
        "task": "backend.tasks.fast_signals.update_fast_signals",
        "schedule": settings.fast_signals_interval,  # 300 seconds
        "options": {
            "queue": "fast",
            "expires": 280,
        },
    },

    # ─────────────────────────────────────────
    # TASK 3: MEDIUM SIGNALS
    # Runs every 30 minutes
    # Updates: DefiLlama stablecoins + Coinglass
    # ─────────────────────────────────────────
    "medium-signals-every-30min": {
        "task": "backend.tasks.medium_signals.update_medium_signals",
        "schedule": settings.medium_signals_interval,  # 1800 seconds
        "options": {
            "queue": "medium",
            "expires": 1750,
        },
    },

    # ─────────────────────────────────────────
    # TASK 4: SLOW SIGNALS
    # Runs every 6 hours
    # Updates: FRED + GitHub + CourtListener
    #          + TokenUnlocks
    # ─────────────────────────────────────────
    "slow-signals-every-6hr": {
        "task": "backend.tasks.slow_signals.update_slow_signals",
        "schedule": settings.slow_signals_interval,  # 21600 seconds
        "options": {
            "queue": "slow",
            "expires": 21000,
        },
    },

    # ─────────────────────────────────────────
    # TASK 5: CLEANUP EXPIRED
    # Runs every 1 hour
    # Resolves expired markets
    # Archives historical opportunities
    # ─────────────────────────────────────────
    "cleanup-expired-every-1hr": {
        "task": "backend.tasks.cleanup.cleanup_expired",
        "schedule": settings.cleanup_interval,  # 3600 seconds
        "options": {
            "queue": "cleanup",
            "expires": 3500,
        },
    },
}