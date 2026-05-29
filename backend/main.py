"""
CAYE v3.0 — FastAPI Application Entry Point
UPDATED IN PHASE 6: WebSocket router mounted.
Broadcaster started in lifespan.
"""

from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from backend.config import get_settings
from backend.database import check_database_connection, init_db
from backend.routers import (
    opportunities,
    signals,
    performance,
    scanlogs,
    health,
    verify
)

# ─────────────────────────────────────────
# PHASE 6: IMPORT WEBSOCKET COMPONENTS
# ─────────────────────────────────────────
from backend.websocket.router import (
    router as websocket_router,
    start_broadcaster,
    stop_broadcaster
)

settings = get_settings()


# ─────────────────────────────────────────
# LIFESPAN (Startup + Shutdown)
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    # ─────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────
    logger.info("=" * 60)
    logger.info("CAYE v3.0 — Starting up...")
    logger.info("=" * 60)

    # Check database connection
    if not check_database_connection():
        logger.error("Database connection failed on startup")
    else:
        logger.info("Database connection: OK")

    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized: OK")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize default signal state if none exists
    try:
        from backend.database import SessionLocal
        from backend.models import SignalState

        db = SessionLocal()
        latest = db.query(SignalState).order_by(
            SignalState.created_at.desc()
        ).first()

        if not latest:
            default_state = SignalState(
                stablecoin_exodus=False,
                macro_draining=False,
                insider_activity=False,
                any_abandonment=False,
                any_over_leveraged=False,
                regulatory_pressure=False,
                major_unlock_imminent=False,
                signal_data_stale=True,
                source_flags={"initialization": "default_state"}
            )
            db.add(default_state)
            db.commit()
            logger.info("Default signal state initialized")
        else:
            logger.info(
                f"Signal state loaded — "
                f"last updated: {latest.created_at}"
            )
        db.close()
    except Exception as e:
        logger.error(
            f"Signal state initialization failed: {e}"
        )

    # ─────────────────────────────────────
    # PHASE 6: START REDIS BROADCASTER
    # ─────────────────────────────────────
    try:
        await start_broadcaster()
        logger.info("WebSocket broadcaster: ONLINE")
    except Exception as e:
        logger.error(
            f"WebSocket broadcaster failed to start: {e}"
        )

    logger.info("CAYE v3.0 — System ONLINE")
    logger.info(f"Dashboard:  http://localhost:3000")
    logger.info(
        f"API Docs:   "
        f"http://localhost:{settings.app_port}/docs"
    )
    logger.info(
        f"WebSocket:  "
        f"ws://localhost:{settings.app_port}/ws"
    )
    logger.info("=" * 60)

    yield

    # ─────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────
    logger.info("CAYE v3.0 — Shutting down...")

    # Stop WebSocket broadcaster
    try:
        await stop_broadcaster()
        logger.info("WebSocket broadcaster: stopped")
    except Exception as e:
        logger.warning(
            f"Broadcaster shutdown error: {e}"
        )

    logger.info("CAYE v3.0 — Shutdown complete")


# ─────────────────────────────────────────
# CREATE FASTAPI APPLICATION
# ─────────────────────────────────────────
app = FastAPI(
    title="CAYE v3.0 — Crypto-Asymmetric Yield Engine",
    description=(
        "Prediction market intelligence system for "
        "Polymarket cryptocurrency and DeFi binary markets. "
        "Identifies structurally mispriced outcomes using "
        "9 live data signals and 4 opportunity detection engines."
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ─────────────────────────────────────────
# CORS MIDDLEWARE
# ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# INCLUDE ALL ROUTERS
# ─────────────────────────────────────────
app.include_router(
    health.router,
    tags=["Health"]
)

app.include_router(
    verify.router,
    prefix="/api/verify",
    tags=["Verification"]
)

app.include_router(
    opportunities.router,
    prefix="/api/opportunities",
    tags=["Opportunities"]
)

app.include_router(
    signals.router,
    prefix="/api/signals",
    tags=["Signals"]
)

app.include_router(
    performance.router,
    prefix="/api/performance",
    tags=["Performance"]
)

app.include_router(
    scanlogs.router,
    prefix="/api/scanlogs",
    tags=["Scan Logs"]
)

# ─────────────────────────────────────────
# PHASE 6: MOUNT WEBSOCKET ROUTER
# ─────────────────────────────────────────
app.include_router(
    websocket_router,
    tags=["WebSocket"]
)


# ─────────────────────────────────────────
# ROOT ENDPOINT
# ─────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "system": "CAYE v3.0",
        "name": "Crypto-Asymmetric Yield Engine",
        "status": "ONLINE",
        "scope": (
            "Polymarket Cryptocurrency & "
            "DeFi Markets ONLY"
        ),
        "version": "3.0.0",
        "docs": "/docs",
        "websocket": "/ws",
        "ws_stats": "/ws/stats",
        "timestamp": datetime.utcnow().isoformat()
    }