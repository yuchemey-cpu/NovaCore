# maturity_engine.py
# NovaCore - Emotional Maturity Engine (0.0 → 1.0)
# This module calculates Nova's emotional maturity score based on
# identity, relationship stage, emotions, mood, and physical needs.

from dataclasses import dataclass
from typing import Optional


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


@dataclass
class MaturityInputs:
    identity_base: float = 0.5           # from identity sheet (0–1)
    relationship_level: int = 0          # 0–7 scale
    mood_balance: float = 0.5            # from mood engine (0–1)
    emotional_intensity: float = 0.0      # 0–1
    emotional_stability: float = 0.5      # fusion stability (0–1)
    need_pressure: float = 0.0            # hunger/thirst/fatigue/bladder (0–1)


class MaturityEngine:
    """
    Calculates Nova's emotional maturity score.
    Higher maturity = calm, composed, emotionally intelligent.
    Lower maturity = more reactive, pouty, vulnerable, flustered.
    """

    def compute(self, data: MaturityInputs) -> float:
        # Convert relationship level (0–7) into maturity weight
        relationship_factor = 1.0 - (data.relationship_level / 7.0)

        # Weighted formula
        maturity = (
            (data.identity_base * 0.30) +
            (relationship_factor * 0.25) +
            (data.mood_balance * 0.15) +
            (data.emotional_stability * 0.10) -
            (data.emotional_intensity * 0.10) -
            (data.need_pressure * 0.10)
        )

        return clamp(maturity)


# Example usage
if __name__ == "__main__":
    engine = MaturityEngine()
    inputs = MaturityInputs(
        identity_base=0.6,
        relationship_level=3,
        mood_balance=0.7,
        emotional_intensity=0.2,
        emotional_stability=0.6,
        need_pressure=0.1,
    )

    score = engine.compute(inputs)
    print("Maturity Score:", score)