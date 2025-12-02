# affection_engine.py
# Manages emotional closeness, affection, arousal, and intimacy readiness.

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import random

@dataclass
class AffectionState:
    affection: float = 0.3         # emotional closeness 0–1
    arousal: float = 0.0           # biological/sexual activation 0–1
    comfort: float = 0.5           # how safe she feels around user 0–1
    fluster: float = 0.0           # shyness/embarrassment 0–1
    readiness: float = 0.0         # NSFW readiness 0–1


class AffectionEngine:
    def __init__(self):
        self.state = AffectionState()

    def update(self, nova_state):
        """
        Updates affection, arousal, comfort, and readiness based on NovaState.
        This does NOT produce explicit output.
        It only affects behavior, tone, hesitation, and intent.
        """

        # 1. Emotional closeness grows with trust
        t = nova_state.relationship.trust
        self.state.affection += (t - self.state.affection) * 0.05

        # 2. Affection increases when mood is positive
        if nova_state.mood.valence > 0.2:
            self.state.affection += 0.02

        # 3. Arousal rises with emotional intensity (but slowly)
        if nova_state.emotion.intensity > 0.4:
            self.state.arousal += 0.015 * nova_state.emotion.intensity

        # 4. Comfort increases with calmness
        if nova_state.emotion.stability > 0.5:
            self.state.comfort += 0.01

        # 5. Fluster rises when affection high + maturity low
        if self.state.affection > 0.55 and nova_state.maturity < 0.5:
            self.state.fluster += 0.02

        # 6. NSFW readiness is blend of affection + arousal + comfort
        self.state.readiness = (
            self.state.affection * 0.4 +
            self.state.arousal * 0.4 +
            self.state.comfort * 0.2
        )

        # Clamp values
        self.state.affection = min(max(self.state.affection, 0), 1)
        self.state.arousal = min(max(self.state.arousal, 0), 1)
        self.state.comfort = min(max(self.state.comfort, 0), 1)
        self.state.fluster = min(max(self.state.fluster, 0), 1)
        self.state.readiness = min(max(self.state.readiness, 0), 1)

        return self.state
