"""
CAYE v3.0 — Signal Engines Package
4 specialized opportunity detection engines.

ENGINE 1: Inverse Trap
  Targets extreme retail consensus markets
  where one side is priced > $0.80

ENGINE 2: Tail-Risk Front-Run
  Targets low-probability tail events
  priced <= $0.15 with structural decay signals

ENGINE 3: Deterministic Unlock Bleed
  Targets token price markets with
  scheduled vesting cliff unlocks > $50M

ENGINE 4: Macro Starvation Short
  Targets bullish price milestone markets
  when Fed liquidity is draining > 2% weekly
"""

from backend.engines.base import BaseEngine, EngineResult
from backend.engines.cis_calculator import CISCalculator
from backend.engines.kelly_sizer import KellySizer
from backend.engines.router import EngineRouter
from backend.engines.engine1_inverse_trap import Engine1InverseTrap
from backend.engines.engine2_tail_risk import Engine2TailRisk
from backend.engines.engine3_unlock_bleed import Engine3UnlockBleed
from backend.engines.engine4_macro_starvation import Engine4MacroStarvation

__all__ = [
    "BaseEngine",
    "EngineResult",
    "CISCalculator",
    "KellySizer",
    "EngineRouter",
    "Engine1InverseTrap",
    "Engine2TailRisk",
    "Engine3UnlockBleed",
    "Engine4MacroStarvation",
]