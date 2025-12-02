# needs_engine.py
# NovaCore - Basic Needs Engine (Sims-like biological model)
#
# Drives: hunger, thirst, fatigue, bladder, affection

from __future__ import annotations

from dataclasses import dataclass
import random
import time


@dataclass
class NeedSnapshot:
    hunger: float = 0.0       # 0.0 - 1.0
    thirst: float = 0.0
    fatigue: float = 0.0
    bladder: float = 0.0
    affection: float = 0.0    # emotional closeness craving

    @property
    def pressure(self) -> float:
        return max(self.hunger, self.thirst, self.fatigue, self.bladder, self.affection)


class NeedsEngine:
    """
    Sim-like biological cycle.
    Tick this once per message or every X seconds.
    """

    def __init__(self):
        self.hunger = 0.1
        self.thirst = 0.1
        self.fatigue = 0.1
        self.bladder = 0.1
        self.affection = 0.2

        self.last_update = time.time()

    def update(self) -> NeedSnapshot:
        """
        Called each turn. Increases needs naturally over time.
        """

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Increase each need slowly + randomness
        self.hunger += dt * 0.0006 + random.uniform(0, 0.005)
        self.thirst += dt * 0.0009 + random.uniform(0, 0.005)
        self.fatigue += dt * 0.0004 + random.uniform(0, 0.003)
        self.bladder += dt * 0.0008 + random.uniform(0, 0.004)
        self.affection += dt * 0.0005 + random.uniform(0, 0.003)

        # Clamp all to 0–1
        self.hunger = min(self.hunger, 1.0)
        self.thirst = min(self.thirst, 1.0)
        self.fatigue = min(self.fatigue, 1.0)
        self.bladder = min(self.bladder, 1.0)
        self.affection = min(self.affection, 1.0)

        return NeedSnapshot(
            hunger=self.hunger,
            thirst=self.thirst,
            fatigue=self.fatigue,
            bladder=self.bladder,
            affection=self.affection,
        )

    # Reset methods for later
    def eat(self): self.hunger = max(0.0, self.hunger - 0.7)
    def drink(self): self.thirst = max(0.0, self.thirst - 0.8)
    def rest(self): self.fatigue = max(0.0, self.fatigue - 0.6)
    def toilet(self): self.bladder = max(0.0, self.bladder - 0.9)
    def receive_affection(self, amount: float = 0.4):
        self.affection = max(0.0, self.affection - amount)
