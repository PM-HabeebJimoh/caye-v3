"""
CAYE v3.0 — Pydantic Schemas
Request/Response validation for all API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ─────────────────────────────────────────
# SIGNAL STATE SCHEMAS
# ─────────────────────────────────────────

class SignalStateResponse(BaseModel):
    id: int
    created_at: datetime
    stablecoin_exodus: bool
    stablecoin_delta_48h: Optional[float]
    total_stablecoin_mcap: Optional[float]
    macro_draining: bool
    weekly_delta_pct: Optional[float]
    current_net_liquidity: Optional[float]
    insider_activity: bool
    gas_acceleration_rate: Optional[float]
    current_gas_gwei: Optional[int]
    any_abandonment: bool
    abandonment_details: Optional[Dict[str, Any]]
    any_over_leveraged: bool
    funding_rate_details: Optional[Dict[str, Any]]
    regulatory_pressure: bool
    total_dockets_7d: Optional[int]
    major_unlock_imminent: bool
    upcoming_unlocks: Optional[List[Dict[str, Any]]]
    spot_prices: Optional[Dict[str, Any]]
    signal_data_stale: bool
    source_flags: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class SignalSummaryResponse(BaseModel):
    """Compact signal state for dashboard display."""
    created_at: datetime
    stablecoin_exodus: bool
    macro_draining: bool
    insider_activity: bool
    any_abandonment: bool
    any_over_leveraged: bool
    regulatory_pressure: bool
    major_unlock_imminent: bool
    signal_data_stale: bool
    active_signal_count: int
    stablecoin_delta_48h: Optional[float]
    weekly_delta_pct: Optional[float]
    current_gas_gwei: Optional[int]
    total_dockets_7d: Optional[int]
    upcoming_unlocks: Optional[List[Dict[str, Any]]]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# OPPORTUNITY SCHEMAS
# ─────────────────────────────────────────

class SignalBreakdown(BaseModel):
    stablecoin_exodus: float = 0.0
    macro_draining: float = 0.0
    insider_activity: float = 0.0
    dev_abandonment: float = 0.0
    over_leveraged: float = 0.0
    regulatory_pressure: float = 0.0
    major_unlock_imminent: float = 0.0
    total: float = 0.0


class GateResults(BaseModel):
    gate1_passed: bool
    gate1_reason: Optional[str]
    gate2_passed: bool
    gate2_reason: Optional[str]
    gate3_passed: bool
    gate3_reason: Optional[str]
    gate4_passed: bool
    gate4_reason: Optional[str]


class OpportunityResponse(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime
    market_id: str
    condition_id: Optional[str]
    question: str
    polymarket_url: Optional[str]
    market_category: str
    subcategory: Optional[str]
    engine_id: int
    engine_name: str
    entry_price: float
    target_side: str
    yes_price_at_entry: Optional[float]
    no_price_at_entry: Optional[float]
    cis_score: float
    signal_breakdown: Optional[Dict[str, Any]]
    gate_results: Optional[Dict[str, Any]]
    recommended_position: float
    potential_profit: float
    roi_pct: float
    kelly_fraction: float
    expected_value: Optional[float]
    liquidity: Optional[float]
    volume: Optional[float]
    expiry_date: Optional[datetime]
    days_to_expiry: Optional[int]
    status: str
    resolved_at: Optional[datetime]
    actual_roi: Optional[float]
    actual_profit: Optional[float]
    resolution_price: Optional[float]

    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    total: int
    opportunities: List[OpportunityResponse]
    page: int
    page_size: int


# ─────────────────────────────────────────
# VETO LOG SCHEMAS
# ─────────────────────────────────────────

class VetoLogResponse(BaseModel):
    id: int
    created_at: datetime
    market_id: Optional[str]
    question: Optional[str]
    gate_number: int
    gate_name: str
    reason: str
    actual_value: Optional[float]
    required_value: Optional[float]
    entry_price: Optional[float]
    engine_id: Optional[int]
    cis_score: Optional[float]
    signal_breakdown: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class VetoLogListResponse(BaseModel):
    total: int
    vetoes: List[VetoLogResponse]


# ─────────────────────────────────────────
# SCAN LOG SCHEMAS
# ─────────────────────────────────────────

class ScanLogResponse(BaseModel):
    id: int
    scanned_at: datetime
    markets_fetched: int
    markets_crypto: int
    markets_vetoed: int
    opportunities_found: int
    gate1_vetoed: int
    gate2_vetoed: int
    gate3_vetoed: int
    gate4_vetoed: int
    scan_duration_ms: Optional[int]
    signal_data_stale: bool
    error_message: Optional[str]

    class Config:
        from_attributes = True


class ScanLogListResponse(BaseModel):
    total: int
    scans: List[ScanLogResponse]


# ─────────────────────────────────────────
# PERFORMANCE SCHEMAS
# ─────────────────────────────────────────

class PerformanceSummaryResponse(BaseModel):
    total_trades: int
    active_trades: int
    won_trades: int
    lost_trades: int
    expired_trades: int
    win_rate: float
    average_roi: float
    total_profit_loss: float
    max_drawdown: float
    best_trade_roi: Optional[float]
    worst_trade_roi: Optional[float]
    engine_breakdown: Dict[str, Any]
    monthly_performance: List[Dict[str, Any]]


class EnginePerformanceResponse(BaseModel):
    engine_id: int
    engine_name: str
    total_trades: int
    won_trades: int
    lost_trades: int
    win_rate: float
    average_roi: float
    total_profit_loss: float


# ─────────────────────────────────────────
# HEALTH CHECK SCHEMAS
# ─────────────────────────────────────────

class ServiceStatus(BaseModel):
    name: str
    status: str
    details: Optional[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    services: List[ServiceStatus]
    timestamp: datetime


# ─────────────────────────────────────────
# CRYPTO VERIFICATION SCHEMAS
# ─────────────────────────────────────────

class CryptoVerificationResponse(BaseModel):
    non_crypto_count: int
    total_opportunities: int
    crypto_enforcement: str
    status: str
    timestamp: datetime


# ─────────────────────────────────────────
# WEBSOCKET EVENT SCHEMAS
# ─────────────────────────────────────────

class WSEventNewOpportunity(BaseModel):
    event: str = "new_opportunity"
    opportunity: OpportunityResponse


class WSEventSignalUpdate(BaseModel):
    event: str = "signal_update"
    signal_state: SignalStateResponse


class WSEventScanComplete(BaseModel):
    event: str = "scan_complete"
    scan_log: ScanLogResponse


class WSEventOpportunityResolved(BaseModel):
    event: str = "opportunity_resolved"
    opportunity_id: int
    status: str
    actual_roi: Optional[float]
    resolved_at: datetime


class WSEventOpportunityExpired(BaseModel):
    event: str = "opportunity_expired"
    opportunity_id: int
    expired_at: datetime


class WSInitialState(BaseModel):
    event: str = "initial_state"
    active_opportunities: List[OpportunityResponse]
    signal_state: Optional[SignalStateResponse]
    last_scan: Optional[ScanLogResponse]
    system_status: str
    timestamp: datetime