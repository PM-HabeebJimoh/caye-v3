"""
CAYE v3.0 — Base Engine Class
All 4 engines inherit from this base.
Defines shared interface and data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from loguru import logger


# ─────────────────────────────────────────
# ENGINE RESULT DATACLASS
# Standardized output from all engines
# ─────────────────────────────────────────

@dataclass
class EngineResult:
    """
    Standardized result object returned by
    all 4 opportunity engines.
    Contains everything needed to evaluate
    and display a trade opportunity.
    """

    # Engine identification
    engine_id: int = 0
    engine_name: str = ""

    # Trade parameters
    entry_price: float = 0.0
    target_side: str = ""      # 'YES' or 'NO'
    yes_price: float = 0.0
    no_price: float = 0.0

    # CIS scoring
    cis_score: float = 0.0
    signal_breakdown: Dict[str, float] = field(
        default_factory=dict
    )

    # Gate results
    gate1_passed: bool = False
    gate1_reason: str = ""
    gate2_passed: bool = False
    gate2_reason: str = ""
    gate3_passed: bool = False
    gate3_reason: str = ""
    gate4_passed: bool = False
    gate4_reason: str = ""
    all_gates_passed: bool = False

    # Position sizing
    recommended_position: float = 0.0
    potential_profit: float = 0.0
    roi_pct: float = 0.0
    kelly_fraction: float = 0.0
    expected_value: float = 0.0

    # Market metadata
    market_id: str = ""
    question: str = ""
    polymarket_url: Optional[str] = None
    subcategory: str = ""
    liquidity: float = 0.0
    volume: float = 0.0
    expiry_date: Optional[str] = None
    days_to_expiry: Optional[int] = None

    # Skip/veto tracking
    should_skip: bool = False
    skip_reason: str = ""

    # Veto tracking (which gate failed)
    vetoed_by_gate: Optional[int] = None
    veto_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id": self.engine_id,
            "engine_name": self.engine_name,
            "entry_price": self.entry_price,
            "target_side": self.target_side,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "cis_score": self.cis_score,
            "signal_breakdown": self.signal_breakdown,
            "gate1_passed": self.gate1_passed,
            "gate1_reason": self.gate1_reason,
            "gate2_passed": self.gate2_passed,
            "gate2_reason": self.gate2_reason,
            "gate3_passed": self.gate3_passed,
            "gate3_reason": self.gate3_reason,
            "gate4_passed": self.gate4_passed,
            "gate4_reason": self.gate4_reason,
            "all_gates_passed": self.all_gates_passed,
            "recommended_position": self.recommended_position,
            "potential_profit": self.potential_profit,
            "roi_pct": self.roi_pct,
            "kelly_fraction": self.kelly_fraction,
            "expected_value": self.expected_value,
            "market_id": self.market_id,
            "question": self.question,
            "polymarket_url": self.polymarket_url,
            "subcategory": self.subcategory,
            "liquidity": self.liquidity,
            "volume": self.volume,
            "expiry_date": self.expiry_date,
            "days_to_expiry": self.days_to_expiry,
            "should_skip": self.should_skip,
            "skip_reason": self.skip_reason,
            "vetoed_by_gate": self.vetoed_by_gate,
            "veto_reason": self.veto_reason,
        }


# ─────────────────────────────────────────
# SIGNAL STATE DATACLASS
# Passed into every engine evaluate() call
# ─────────────────────────────────────────

@dataclass
class SignalState:
    """
    Current boolean state of all 7 signals.
    Read from signal_state DB table.
    Passed into every engine for CIS calculation.
    """

    # Signal 3: DefiLlama
    stablecoin_exodus: bool = False

    # Signal 5: FRED
    macro_draining: bool = False

    # Signal 4: Etherscan
    insider_activity: bool = False

    # Signal 6: GitHub
    any_abandonment: bool = False

    # Signal 8: Coinglass
    any_over_leveraged: bool = False

    # Signal 7: CourtListener
    regulatory_pressure: bool = False

    # Signal 9: TokenUnlocks
    major_unlock_imminent: bool = False

    # Meta
    signal_data_stale: bool = False

    @classmethod
    def from_db_record(cls, record) -> "SignalState":
        """
        Creates SignalState from SQLAlchemy model instance.
        """
        if not record:
            return cls(signal_data_stale=True)

        return cls(
            stablecoin_exodus=record.stablecoin_exodus or False,
            macro_draining=record.macro_draining or False,
            insider_activity=record.insider_activity or False,
            any_abandonment=record.any_abandonment or False,
            any_over_leveraged=record.any_over_leveraged or False,
            regulatory_pressure=record.regulatory_pressure or False,
            major_unlock_imminent=record.major_unlock_imminent or False,
            signal_data_stale=record.signal_data_stale or False,
        )

    def active_count(self) -> int:
        """
        Returns count of currently active signals.
        """
        return sum([
            self.stablecoin_exodus,
            self.macro_draining,
            self.insider_activity,
            self.any_abandonment,
            self.any_over_leveraged,
            self.regulatory_pressure,
            self.major_unlock_imminent,
        ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stablecoin_exodus": self.stablecoin_exodus,
            "macro_draining": self.macro_draining,
            "insider_activity": self.insider_activity,
            "any_abandonment": self.any_abandonment,
            "any_over_leveraged": self.any_over_leveraged,
            "regulatory_pressure": self.regulatory_pressure,
            "major_unlock_imminent": self.major_unlock_imminent,
            "signal_data_stale": self.signal_data_stale,
            "active_count": self.active_count(),
        }


# ─────────────────────────────────────────
# BASE ENGINE CLASS
# All 4 engines inherit from this
# ─────────────────────────────────────────

class BaseEngine(ABC):
    """
    Abstract base class for all 4 CAYE engines.
    Provides shared gate enforcement and
    position sizing logic.
    Each engine implements evaluate() method.
    """

    ENGINE_ID: int = 0
    ENGINE_NAME: str = "Base Engine"

    # Gate thresholds (from spec)
    PRICE_CEILING: float = 0.52       # Gate 1
    CIS_THRESHOLD: float = 0.89       # Gate 2
    MIN_LIQUIDITY: float = 50_000.0   # Gate 3
    MIN_DAYS_TO_EXPIRY: int = 2       # Gate 4

    def __init__(self):
        from backend.engines.cis_calculator import CISCalculator
        from backend.engines.kelly_sizer import KellySizer
        self.cis_calculator = CISCalculator()
        self.kelly_sizer = KellySizer()

    @abstractmethod
    def evaluate(
        self,
        market: Dict[str, Any],
        signal_state: SignalState,
        spot_prices: Dict[str, Any],
        bankroll: float = 10000.0
    ) -> EngineResult:
        """
        Evaluates a single market for this engine.
        Returns EngineResult with all_gates_passed=True
        if the market is a valid trade opportunity.
        """
        pass

    def _build_base_result(
        self,
        market: Dict[str, Any]
    ) -> EngineResult:
        """
        Creates a base EngineResult populated
        with market metadata.
        """
        return EngineResult(
            engine_id=self.ENGINE_ID,
            engine_name=self.ENGINE_NAME,
            market_id=market.get("market_id", ""),
            question=market.get("question", ""),
            polymarket_url=market.get("polymarket_url"),
            subcategory=market.get("subcategory", ""),
            liquidity=float(market.get("liquidity", 0) or 0),
            volume=float(market.get("volume", 0) or 0),
            expiry_date=market.get("end_date"),
            days_to_expiry=market.get("days_to_expiry"),
            yes_price=float(market.get("yes_price", 0.5)),
            no_price=float(market.get("no_price", 0.5)),
        )

    def _skip(
        self,
        result: EngineResult,
        reason: str
    ) -> EngineResult:
        """
        Marks result as skipped (no applicable engine).
        Not a gate veto — just not relevant to this engine.
        """
        result.should_skip = True
        result.skip_reason = reason
        return result

    # ─────────────────────────────────────
    # GATE ENFORCEMENT
    # Run in order: 3 → 1 → 4 → 2
    # ─────────────────────────────────────

    def _enforce_gate3_liquidity(
        self,
        result: EngineResult
    ) -> bool:
        """
        Gate 3: Liquidity >= $50,000
        Fastest check — no CIS needed.
        Returns True if PASSES.
        """
        liquidity = result.liquidity

        if liquidity >= self.MIN_LIQUIDITY:
            result.gate3_passed = True
            result.gate3_reason = (
                f"Liquidity ${liquidity:,.0f} "
                f">= ${self.MIN_LIQUIDITY:,.0f} ✓"
            )
            return True
        else:
            result.gate3_passed = False
            result.gate3_reason = (
                f"Liquidity ${liquidity:,.0f} "
                f"below ${self.MIN_LIQUIDITY:,.0f} minimum"
            )
            result.vetoed_by_gate = 3
            result.veto_reason = result.gate3_reason
            return False

    def _enforce_gate1_price(
        self,
        result: EngineResult,
        entry_price: float
    ) -> bool:
        """
        Gate 1: Entry price <= $0.52
        Guarantees minimum 92.3% ROI if correct.
        Returns True if PASSES.
        """
        if entry_price <= self.PRICE_CEILING:
            roi = (1.0 / entry_price - 1) * 100
            result.gate1_passed = True
            result.gate1_reason = (
                f"Entry ${entry_price:.2f} "
                f"<= ${self.PRICE_CEILING:.2f} ceiling "
                f"(Min ROI: {roi:.1f}%) ✓"
            )
            return True
        else:
            actual_roi = (1.0 / entry_price - 1) * 100
            result.gate1_passed = False
            result.gate1_reason = (
                f"Entry ${entry_price:.2f} "
                f"exceeds ${self.PRICE_CEILING:.2f} ceiling. "
                f"ROI would be {actual_roi:.1f}% (need >90%)"
            )
            result.vetoed_by_gate = 1
            result.veto_reason = result.gate1_reason
            return False

    def _enforce_gate4_expiry(
        self,
        result: EngineResult
    ) -> bool:
        """
        Gate 4: Market expires > 2 days from now.
        Thesis needs time to manifest.
        Returns True if PASSES.
        """
        days = result.days_to_expiry

        if days is None:
            result.gate4_passed = False
            result.gate4_reason = "No expiry date available"
            result.vetoed_by_gate = 4
            result.veto_reason = result.gate4_reason
            return False

        if days > self.MIN_DAYS_TO_EXPIRY:
            result.gate4_passed = True
            result.gate4_reason = (
                f"Expires in {days} days "
                f"> {self.MIN_DAYS_TO_EXPIRY} days ✓"
            )
            return True
        else:
            result.gate4_passed = False
            result.gate4_reason = (
                f"Market expires in {days} days. "
                f"Insufficient time for thesis "
                f"(need > {self.MIN_DAYS_TO_EXPIRY} days)"
            )
            result.vetoed_by_gate = 4
            result.veto_reason = result.gate4_reason
            return False

    def _enforce_gate2_cis(
        self,
        result: EngineResult,
        cis_score: float,
        signal_breakdown: Dict[str, float]
    ) -> bool:
        """
        Gate 2: CIS score >= 0.89
        Most expensive gate — calculated last.
        Returns True if PASSES.
        """
        result.cis_score = round(cis_score, 4)
        result.signal_breakdown = signal_breakdown

        if cis_score >= self.CIS_THRESHOLD:
            result.gate2_passed = True
            result.gate2_reason = (
                f"CIS {cis_score:.4f} "
                f">= {self.CIS_THRESHOLD} threshold ✓"
            )
            return True
        else:
            result.gate2_passed = False
            result.gate2_reason = (
                f"CIS {cis_score:.4f} "
                f"below {self.CIS_THRESHOLD} threshold. "
                f"Insufficient signal convergence."
            )
            result.vetoed_by_gate = 2
            result.veto_reason = result.gate2_reason
            return False

    def _apply_kelly_sizing(
        self,
        result: EngineResult,
        entry_price: float,
        cis_score: float,
        bankroll: float
    ) -> EngineResult:
        """
        Applies Quarter-Kelly position sizing
        after all gates pass.
        """
        kelly_result = self.kelly_sizer.calculate(
            entry_price=entry_price,
            cis_score=cis_score,
            bankroll=bankroll
        )

        result.recommended_position = kelly_result["position_size"]
        result.potential_profit = kelly_result["potential_profit"]
        result.roi_pct = kelly_result["roi_pct"]
        result.kelly_fraction = kelly_result["kelly_fraction"]
        result.expected_value = kelly_result["expected_value"]

        return result

    def _finalize_pass(
        self,
        result: EngineResult
    ) -> EngineResult:
        """
        Marks result as fully passed all gates.
        """
        result.all_gates_passed = True
        result.should_skip = False
        result.skip_reason = ""

        logger.info(
            f"Engine {self.ENGINE_ID} [{self.ENGINE_NAME}]: "
            f"OPPORTUNITY FOUND "
            f"CIS={result.cis_score:.4f} "
            f"Entry=${result.entry_price:.2f} "
            f"Side={result.target_side} "
            f"ROI={result.roi_pct:.1f}% "
            f"Pos=${result.recommended_position:,.0f}"
        )

        return result