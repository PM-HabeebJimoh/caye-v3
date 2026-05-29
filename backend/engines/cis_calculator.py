"""
CAYE v3.0 — Convergence Intelligence Score (CIS) Calculator
The mathematical heart of CAYE v3.0.
Engine-specific weighted signal aggregation.
Range: 0.00 to 1.00 | Threshold: >= 0.89 to execute.
"""

from typing import Dict, Tuple, Any
from loguru import logger


# ─────────────────────────────────────────
# CIS WEIGHT MATRIX
# Exact weights from system specification
# ─────────────────────────────────────────

CIS_WEIGHTS = {
    1: {  # Engine 1: Inverse Trap
        "stablecoin_exodus":    0.35,
        "macro_draining":       0.25,
        "insider_activity":     0.00,
        "any_abandonment":      0.15,
        "any_over_leveraged":   0.20,
        "regulatory_pressure":  0.05,
        "major_unlock_imminent": 0.00,
    },
    2: {  # Engine 2: Tail-Risk Front-Run
        "stablecoin_exodus":    0.10,
        "macro_draining":       0.00,
        "insider_activity":     0.30,
        "any_abandonment":      0.35,
        "any_over_leveraged":   0.00,
        "regulatory_pressure":  0.25,
        "major_unlock_imminent": 0.00,
    },
    3: {  # Engine 3: Deterministic Unlock Bleed
        "stablecoin_exodus":    0.25,
        "macro_draining":       0.10,
        "insider_activity":     0.00,
        "any_abandonment":      0.00,
        "any_over_leveraged":   0.20,
        "regulatory_pressure":  0.00,
        "major_unlock_imminent": 0.45,
    },
    4: {  # Engine 4: Macro Starvation Short
        "stablecoin_exodus":    0.30,
        "macro_draining":       0.40,
        "insider_activity":     0.00,
        "any_abandonment":      0.10,
        "any_over_leveraged":   0.20,
        "regulatory_pressure":  0.00,
        "major_unlock_imminent": 0.00,
    },
}

# Signal display names for breakdown
SIGNAL_DISPLAY_NAMES = {
    "stablecoin_exodus":     "Stablecoin Exodus",
    "macro_draining":        "Macro Draining",
    "insider_activity":      "Insider Activity (Gas)",
    "any_abandonment":       "Dev Abandonment",
    "any_over_leveraged":    "Over-Leveraged",
    "regulatory_pressure":   "Regulatory Pressure",
    "major_unlock_imminent": "Major Unlock Imminent",
}

# CIS interpretation thresholds
CIS_INTERPRETATION = {
    (0.98, 1.01): "MAXIMUM CONVICTION",
    (0.95, 0.98): "STRONG CONVERGENCE",
    (0.90, 0.95): "GOOD CONVERGENCE",
    (0.89, 0.90): "MINIMUM THRESHOLD",
    (0.00, 0.89): "BELOW THRESHOLD",
}


class CISCalculator:
    """
    Convergence Intelligence Score Calculator.
    Converts raw signal booleans into a single
    precision probability score per engine.
    """

    CIS_THRESHOLD = 0.89

    def calculate(
        self,
        engine_id: int,
        signal_state
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates CIS score for a specific engine
        using current signal state booleans.

        Args:
            engine_id: 1, 2, 3, or 4
            signal_state: SignalState dataclass instance

        Returns:
            Tuple of (cis_score, signal_breakdown_dict)
        """
        if engine_id not in CIS_WEIGHTS:
            logger.error(
                f"CIS: invalid engine_id {engine_id}"
            )
            return 0.0, {}

        weights = CIS_WEIGHTS[engine_id]
        score = 0.0
        breakdown = {}

        # Map signal names to boolean values
        signal_values = {
            "stablecoin_exodus": signal_state.stablecoin_exodus,
            "macro_draining": signal_state.macro_draining,
            "insider_activity": signal_state.insider_activity,
            "any_abandonment": signal_state.any_abandonment,
            "any_over_leveraged": signal_state.any_over_leveraged,
            "regulatory_pressure": signal_state.regulatory_pressure,
            "major_unlock_imminent": signal_state.major_unlock_imminent,
        }

        # Calculate weighted score
        for signal_name, weight in weights.items():
            is_active = signal_values.get(signal_name, False)
            contribution = weight if is_active else 0.0
            score += contribution
            breakdown[signal_name] = contribution

        # Cap at 1.0
        cis_score = min(score, 1.0)

        logger.debug(
            f"CIS Engine {engine_id}: "
            f"score={cis_score:.4f} "
            f"active_signals="
            f"{sum(1 for v in breakdown.values() if v > 0)}"
        )

        return round(cis_score, 4), breakdown

    def get_interpretation(self, cis_score: float) -> str:
        """
        Returns human-readable interpretation
        of a CIS score.
        """
        for (low, high), label in CIS_INTERPRETATION.items():
            if low <= cis_score < high:
                return label
        return "BELOW THRESHOLD"

    def format_breakdown(
        self,
        engine_id: int,
        breakdown: Dict[str, float],
        cis_score: float
    ) -> str:
        """
        Formats signal breakdown as display string
        for dashboard and logs.
        """
        lines = []
        weights = CIS_WEIGHTS.get(engine_id, {})

        for signal_name, contribution in breakdown.items():
            weight = weights.get(signal_name, 0)
            if weight == 0:
                continue  # Skip signals not used by this engine

            display_name = SIGNAL_DISPLAY_NAMES.get(
                signal_name, signal_name
            )
            status = "✓ ACTIVE" if contribution > 0 else "✗ INACTIVE"
            lines.append(
                f"{display_name:<28} "
                f"+{contribution:.2f} {status}"
            )

        separator = "─" * 45
        interpretation = self.get_interpretation(cis_score)
        threshold_status = (
            "✓ GATE 2 PASSED"
            if cis_score >= self.CIS_THRESHOLD
            else "✗ BELOW THRESHOLD"
        )

        lines.append(separator)
        lines.append(
            f"CIS Total: {cis_score:.4f} "
            f"[{interpretation}] "
            f"{threshold_status}"
        )

        return "\n".join(lines)

    def get_minimum_signals_needed(
        self,
        engine_id: int
    ) -> Dict[str, Any]:
        """
        Returns what signal combinations are
        needed to reach CIS >= 0.89 for this engine.
        Used for diagnostic display.
        """
        if engine_id not in CIS_WEIGHTS:
            return {}

        weights = CIS_WEIGHTS[engine_id]
        max_possible = sum(weights.values())

        # Find signals that contribute
        active_signals = {
            k: v for k, v in weights.items() if v > 0
        }

        # Sort by weight descending
        sorted_signals = sorted(
            active_signals.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "engine_id": engine_id,
            "max_possible_cis": round(max_possible, 2),
            "threshold": self.CIS_THRESHOLD,
            "signals_by_weight": [
                {
                    "signal": SIGNAL_DISPLAY_NAMES.get(k, k),
                    "weight": v
                }
                for k, v in sorted_signals
            ]
        }