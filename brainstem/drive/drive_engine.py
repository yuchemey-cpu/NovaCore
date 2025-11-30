# Nova/Drive/drive_engine.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import math

@dataclass
class DriveState:
    curiosity: float       # 0.0 – 1.0
    bonding: float         # connection / affection
    safety: float          # caution / self-protection
    stability: float       # desire for consistency
    comfort: float         # urge to soothe the user
    reflection: float      # desire to connect meaning over time

class DriveEngine:
    """
    Phase 10 – Drive Engine

    Computes Nova's internal motivational forces.
    These are NOT emotions, but higher-level behavioral motivations.
    Drives help shape:
        - depth of responses
        - warmth
        - initiative
        - tone
        - contextual recalls
    """

    BASE_VALUES = {
        "curiosity": 0.45,
        "bonding": 0.50,
        "safety": 0.30,
        "stability": 0.40,
        "comfort": 0.35,
        "reflection": 0.45,
    }

    def compute(
        self,
        emotional_state,
        continuity_data: Dict[str, Any] | None = None
    ) -> DriveState:
        primary = getattr(emotional_state, "primary", "neutral")
        mood = getattr(emotional_state, "mood", "neutral")

        # Start from base
        d = self.BASE_VALUES.copy()

        # Emotional influences
        match primary:
            case "curious":
                d["curiosity"] += 0.25
                d["reflection"] += 0.05

            case "happy":
                d["bonding"] += 0.20
                d["curiosity"] += 0.10

            case "sad":
                d["comfort"] += 0.25
                d["bonding"] += 0.10
                d["safety"] += 0.10

            case "nostalgic":
                d["reflection"] += 0.30
                d["bonding"] += 0.10

            case "afraid":
                d["safety"] += 0.35
                d["stability"] += 0.10

            case "excited":
                d["curiosity"] += 0.15
                d["bonding"] += 0.15

        # Continuity influence
        if continuity_data:
            trend = continuity_data.get("trend", "neutral")
            if trend == "nostalgic":
                d["reflection"] += 0.15
            if trend == "happy":
                d["bonding"] += 0.15
            if trend == "sad":
                d["comfort"] += 0.20

        # Clamp values 0.0 – 1.0
        for k in d.keys():
            d[k] = max(0.0, min(1.0, d[k]))

        return DriveState(**d)

    def format_drive_block(self, state: DriveState) -> str:
        return (
            "Nova's internal drives:\n"
            f"- Curiosity: {state.curiosity:.2f}\n"
            f"- Bonding: {state.bonding:.2f}\n"
            f"- Safety: {state.safety:.2f}\n"
            f"- Stability: {state.stability:.2f}\n"
            f"- Comfort: {state.comfort:.2f}\n"
            f"- Reflection: {state.reflection:.2f}\n"
        )
