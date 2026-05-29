"""
CAYE v3.0 — SQLAlchemy Database Models
All tables matching the Alembic migration schema exactly.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, Boolean, String,
    Text, DateTime, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from backend.database import Base


# ─────────────────────────────────────────
# SIGNAL STATE MODEL
# Stores all 9 signal boolean states
# ─────────────────────────────────────────
class SignalState(Base):
    __tablename__ = "signal_state"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Signal 3: DefiLlama
    stablecoin_exodus = Column(Boolean, nullable=False, default=False)
    stablecoin_delta_48h = Column(Float, nullable=True)
    total_stablecoin_mcap = Column(Float, nullable=True)

    # Signal 5: FRED
    macro_draining = Column(Boolean, nullable=False, default=False)
    weekly_delta_pct = Column(Float, nullable=True)
    current_net_liquidity = Column(Float, nullable=True)

    # Signal 4: Etherscan
    insider_activity = Column(Boolean, nullable=False, default=False)
    gas_acceleration_rate = Column(Float, nullable=True)
    current_gas_gwei = Column(Integer, nullable=True)

    # Signal 6: GitHub
    any_abandonment = Column(Boolean, nullable=False, default=False)
    abandonment_details = Column(JSONB, nullable=True)

    # Signal 8: Coinglass
    any_over_leveraged = Column(Boolean, nullable=False, default=False)
    funding_rate_details = Column(JSONB, nullable=True)

    # Signal 7: CourtListener
    regulatory_pressure = Column(Boolean, nullable=False, default=False)
    total_dockets_7d = Column(Integer, nullable=True)

    # Signal 9: TokenUnlocks
    major_unlock_imminent = Column(Boolean, nullable=False, default=False)
    upcoming_unlocks = Column(JSONB, nullable=True)

    # Signal 2: CoinGecko
    spot_prices = Column(JSONB, nullable=True)

    # Meta
    signal_data_stale = Column(Boolean, nullable=False, default=False)
    source_flags = Column(JSONB, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "stablecoin_exodus": self.stablecoin_exodus,
            "stablecoin_delta_48h": self.stablecoin_delta_48h,
            "total_stablecoin_mcap": self.total_stablecoin_mcap,
            "macro_draining": self.macro_draining,
            "weekly_delta_pct": self.weekly_delta_pct,
            "current_net_liquidity": self.current_net_liquidity,
            "insider_activity": self.insider_activity,
            "gas_acceleration_rate": self.gas_acceleration_rate,
            "current_gas_gwei": self.current_gas_gwei,
            "any_abandonment": self.any_abandonment,
            "abandonment_details": self.abandonment_details,
            "any_over_leveraged": self.any_over_leveraged,
            "funding_rate_details": self.funding_rate_details,
            "regulatory_pressure": self.regulatory_pressure,
            "total_dockets_7d": self.total_dockets_7d,
            "major_unlock_imminent": self.major_unlock_imminent,
            "upcoming_unlocks": self.upcoming_unlocks,
            "spot_prices": self.spot_prices,
            "signal_data_stale": self.signal_data_stale,
            "source_flags": self.source_flags,
        }


# ─────────────────────────────────────────
# OPPORTUNITY MODEL
# Active and historical trade opportunities
# ─────────────────────────────────────────
class Opportunity(Base):
    __tablename__ = "opportunities"

    __table_args__ = (
        CheckConstraint(
            "market_category = 'CRYPTO'",
            name="crypto_only_constraint"
        ),
        CheckConstraint(
            "status IN ('ACTIVE','VETOED','EXPIRED','WON','LOST')",
            name="valid_status_constraint"
        ),
        CheckConstraint(
            "target_side IN ('YES', 'NO')",
            name="valid_side_constraint"
        ),
        CheckConstraint(
            "engine_id IN (1, 2, 3, 4)",
            name="valid_engine_constraint"
        ),
        CheckConstraint(
            "entry_price > 0 AND entry_price <= 0.52",
            name="price_ceiling_constraint"
        ),
        CheckConstraint(
            "cis_score >= 0.89 AND cis_score <= 1.0",
            name="cis_threshold_constraint"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Market identification
    market_id = Column(String(255), nullable=False, index=True)
    condition_id = Column(String(255), nullable=True)
    question = Column(Text, nullable=False)
    polymarket_url = Column(String(500), nullable=True)
    market_category = Column(String(50), nullable=False, default="CRYPTO")
    subcategory = Column(String(100), nullable=True)

    # Engine
    engine_id = Column(Integer, nullable=False)
    engine_name = Column(String(100), nullable=False)

    # Trade parameters
    entry_price = Column(Float, nullable=False)
    target_side = Column(String(10), nullable=False)
    yes_price_at_entry = Column(Float, nullable=True)
    no_price_at_entry = Column(Float, nullable=True)

    # CIS
    cis_score = Column(Float, nullable=False)
    signal_breakdown = Column(JSONB, nullable=True)
    gate_results = Column(JSONB, nullable=True)

    # Position sizing
    recommended_position = Column(Float, nullable=False)
    potential_profit = Column(Float, nullable=False)
    roi_pct = Column(Float, nullable=False)
    kelly_fraction = Column(Float, nullable=False)
    expected_value = Column(Float, nullable=True)

    # Market metadata
    liquidity = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    days_to_expiry = Column(Integer, nullable=True)

    # Status lifecycle
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)

    # Resolution
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    actual_roi = Column(Float, nullable=True)
    actual_profit = Column(Float, nullable=True)
    resolution_price = Column(Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "market_id": self.market_id,
            "condition_id": self.condition_id,
            "question": self.question,
            "polymarket_url": self.polymarket_url,
            "market_category": self.market_category,
            "subcategory": self.subcategory,
            "engine_id": self.engine_id,
            "engine_name": self.engine_name,
            "entry_price": self.entry_price,
            "target_side": self.target_side,
            "yes_price_at_entry": self.yes_price_at_entry,
            "no_price_at_entry": self.no_price_at_entry,
            "cis_score": self.cis_score,
            "signal_breakdown": self.signal_breakdown,
            "gate_results": self.gate_results,
            "recommended_position": self.recommended_position,
            "potential_profit": self.potential_profit,
            "roi_pct": self.roi_pct,
            "kelly_fraction": self.kelly_fraction,
            "expected_value": self.expected_value,
            "liquidity": self.liquidity,
            "volume": self.volume,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "days_to_expiry": self.days_to_expiry,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "actual_roi": self.actual_roi,
            "actual_profit": self.actual_profit,
            "resolution_price": self.resolution_price,
        }


# ─────────────────────────────────────────
# VETO LOG MODEL
# Records all gate rejections with reasons
# ─────────────────────────────────────────
class VetoLog(Base):
    __tablename__ = "veto_log"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    market_id = Column(String(255), nullable=True)
    question = Column(Text, nullable=True)
    gate_number = Column(Integer, nullable=False, index=True)
    gate_name = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    actual_value = Column(Float, nullable=True)
    required_value = Column(Float, nullable=True)
    entry_price = Column(Float, nullable=True)
    engine_id = Column(Integer, nullable=True)
    cis_score = Column(Float, nullable=True)
    signal_breakdown = Column(JSONB, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "market_id": self.market_id,
            "question": self.question,
            "gate_number": self.gate_number,
            "gate_name": self.gate_name,
            "reason": self.reason,
            "actual_value": self.actual_value,
            "required_value": self.required_value,
            "entry_price": self.entry_price,
            "engine_id": self.engine_id,
            "cis_score": self.cis_score,
            "signal_breakdown": self.signal_breakdown,
        }


# ─────────────────────────────────────────
# SCAN LOG MODEL
# Records every market scan run statistics
# ─────────────────────────────────────────
class ScanLog(Base):
    __tablename__ = "scan_log"

    id = Column(Integer, primary_key=True, index=True)
    scanned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    markets_fetched = Column(Integer, nullable=False, default=0)
    markets_crypto = Column(Integer, nullable=False, default=0)
    markets_vetoed = Column(Integer, nullable=False, default=0)
    opportunities_found = Column(Integer, nullable=False, default=0)
    gate1_vetoed = Column(Integer, nullable=False, default=0)
    gate2_vetoed = Column(Integer, nullable=False, default=0)
    gate3_vetoed = Column(Integer, nullable=False, default=0)
    gate4_vetoed = Column(Integer, nullable=False, default=0)
    scan_duration_ms = Column(Integer, nullable=True)
    signal_data_stale = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "scanned_at": self.scanned_at.isoformat() if self.scanned_at else None,
            "markets_fetched": self.markets_fetched,
            "markets_crypto": self.markets_crypto,
            "markets_vetoed": self.markets_vetoed,
            "opportunities_found": self.opportunities_found,
            "gate1_vetoed": self.gate1_vetoed,
            "gate2_vetoed": self.gate2_vetoed,
            "gate3_vetoed": self.gate3_vetoed,
            "gate4_vetoed": self.gate4_vetoed,
            "scan_duration_ms": self.scan_duration_ms,
            "signal_data_stale": self.signal_data_stale,
            "error_message": self.error_message,
        }


# ─────────────────────────────────────────
# STABLECOIN SNAPSHOTS MODEL
# Historical stablecoin market cap data
# ─────────────────────────────────────────
class StablecoinSnapshot(Base):
    __tablename__ = "stablecoin_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    usdt_mcap = Column(Float, nullable=True)
    usdc_mcap = Column(Float, nullable=True)
    total_mcap = Column(Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "usdt_mcap": self.usdt_mcap,
            "usdc_mcap": self.usdc_mcap,
            "total_mcap": self.total_mcap,
        }


# ─────────────────────────────────────────
# GAS SNAPSHOTS MODEL
# Historical Ethereum gas price data
# ─────────────────────────────────────────
class GasSnapshot(Base):
    __tablename__ = "gas_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    gas_price_gwei = Column(Integer, nullable=False)
    propose_gas_price = Column(Integer, nullable=True)
    fast_gas_price = Column(Integer, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "gas_price_gwei": self.gas_price_gwei,
            "propose_gas_price": self.propose_gas_price,
            "fast_gas_price": self.fast_gas_price,
        }


# ─────────────────────────────────────────
# GITHUB SNAPSHOTS MODEL
# Developer commit velocity history
# ─────────────────────────────────────────
class GitHubSnapshot(Base):
    __tablename__ = "github_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    repo = Column(String(255), nullable=False, index=True)
    recent_avg_commits = Column(Float, nullable=True)
    prior_avg_commits = Column(Float, nullable=True)
    velocity_ratio = Column(Float, nullable=True)
    abandonment_detected = Column(Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "repo": self.repo,
            "recent_avg_commits": self.recent_avg_commits,
            "prior_avg_commits": self.prior_avg_commits,
            "velocity_ratio": self.velocity_ratio,
            "abandonment_detected": self.abandonment_detected,
        }


# ─────────────────────────────────────────
# HISTORICAL OPPORTUNITIES MODEL
# Archive of all resolved/expired trades
# ─────────────────────────────────────────
class HistoricalOpportunity(Base):
    __tablename__ = "historical_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_id = Column(Integer, nullable=False)
    archived_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    market_id = Column(String(255), nullable=True)
    question = Column(Text, nullable=True)
    polymarket_url = Column(String(500), nullable=True)
    engine_id = Column(Integer, nullable=True)
    engine_name = Column(String(100), nullable=True)
    entry_price = Column(Float, nullable=True)
    target_side = Column(String(10), nullable=True)
    cis_score = Column(Float, nullable=True)
    recommended_position = Column(Float, nullable=True)
    roi_pct = Column(Float, nullable=True)
    status = Column(String(50), nullable=True, index=True)
    actual_roi = Column(Float, nullable=True)
    actual_profit = Column(Float, nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    signal_breakdown = Column(JSONB, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "market_id": self.market_id,
            "question": self.question,
            "polymarket_url": self.polymarket_url,
            "engine_id": self.engine_id,
            "engine_name": self.engine_name,
            "entry_price": self.entry_price,
            "target_side": self.target_side,
            "cis_score": self.cis_score,
            "recommended_position": self.recommended_position,
            "roi_pct": self.roi_pct,
            "status": self.status,
            "actual_roi": self.actual_roi,
            "actual_profit": self.actual_profit,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "signal_breakdown": self.signal_breakdown,
        }