# memory_consolidation.py
# NovaCore - Hippocampus Memory Consolidation Engine

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import random
import math


@dataclass
class ConsolidatedMemory:
    text: str
    emotional_weight: float
    relationship_weight: float
    novelty: float
    overall_strength: float
    turns_ago: int = 0


class MemoryConsolidationEngine:
    """
    Takes recent memory (short-term), scores it, 
    promotes important ones into episodic memory,
    and decays old episodic stuff.
    """

    def __init__(self):
        # nothing complex stored here; NovaState carries memory
        pass

    def consolidate(self, nova_state):
        """
        Main entry: consolidates memory each turn.
        """

        recent_list = nova_state.recent_memory
        new_episodic = []

        for mem in recent_list:
            if score := self._score_memory(mem, nova_state):
                if score.overall_strength > 0.35:
                    # promote to episodic memory
                    new_episodic.append(score)

        # Add newly promoted memories
        for e in new_episodic:
            nova_state.episodic_memory.append(e)

        # Decay old episodic memories
        self._decay_episodic(nova_state)

        # Clear short-term memory (we processed it)
        nova_state.recent_memory.clear()

    # ---------- internal scoring methods ----------

    def _score_memory(self, mem, nova_state) -> ConsolidatedMemory | None:
        """
        Evaluate the importance of a memory.
        Returns ConsolidatedMemory or None.
        """

        text = mem.text.lower()
        emotional = nova_state.emotion.intensity
        relationship = nova_state.relationship.trust
        affection = nova_state.affection if hasattr(nova_state, "affection") else 0.3
        arousal = nova_state.arousal if hasattr(nova_state, "arousal") else 0.0
        fluster = nova_state.fluster if hasattr(nova_state, "fluster") else 0.0

        # basic novelty estimate
        novelty = random.uniform(0.1, 0.4)
        if len(text) > 40:
            novelty += 0.1

        # emotional weight
        emotional_weight = emotional * 0.6 + fluster * 0.2 + arousal * 0.2

        # relationship weight
        relationship_weight = (
            relationship * 0.5 +
            affection * 0.3 +
            (1 if "thank" in text else 0) * 0.1 +
            (1 if "love" in text else 0) * 0.2
        )

        # total strength
        strength = (
            emotional_weight * 0.4 +
            relationship_weight * 0.4 +
            novelty * 0.2
        )

        # discard completely unimportant stuff
        if strength < 0.15:
            return None

        return ConsolidatedMemory(
            text=mem.text,
            emotional_weight=emotional_weight,
            relationship_weight=relationship_weight,
            novelty=novelty,
            overall_strength=strength,
        )

    # ---------- decay ----------

    def _decay_episodic(self, nova_state):
        """
        Slowly fade memories over time.
        Strong ones last longer.
        """

        survivors = []
        for mem in nova_state.episodic_memory:
            mem.turns_ago += 1

            # fade rate
            decay = 0.01 + (mem.turns_ago * 0.0005)
            mem.overall_strength -= decay

            if mem.overall_strength > 0.05:
                survivors.append(mem)

        nova_state.episodic_memory = survivors
