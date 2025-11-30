
# Nova/Emotion/emotional_state.py

"""
EmotionalState – Nova's "heart".

This module defines a lightweight emotional state object that:
- tracks Nova's baseline (core emotional gravity)
- tracks current mood (recent trend)
- tracks the immediate emotion of the last event
- keeps a short history for mood calculation
- can be serialized to/from dict for saving in memory files

Designed to be:
- tiny and fast (safe while gaming)
- easy to extend later (intensity, fatigue, etc.)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import time


@dataclass
class EmotionalState:
    
    baseline: str = "curious"
    mood: str = "neutral"
    primary: str = "neutral"
    secondary: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    last_update_ts: float = field(default_factory=time.time)

    # Layer X – emergent fusion emotion (e.g. "insecure", "mischievous")
    fusion: Optional[str] = None

    # When fusion was last updated (for decay / drift)
    last_fusion_update: float = field(default_factory=time.time)


    def push_emotion(self, emotion: Optional[str], max_history: int = 20) -> None:
        """
        Register a new immediate emotion and update the history.

        This should be called by the emotion engine whenever a new
        emotion is computed from an event or user message.
        """
        if not emotion:
            return

        self.primary = emotion
        self.history.append(emotion)

        # keep history bounded for performance
        if len(self.history) > max_history:
            # drop the oldest
            self.history = self.history[-max_history:]

        self.last_update_ts = time.time()

    def set_baseline(self, new_baseline: str) -> None:
        """
        User-controlled or slowly evolving core emotional gravity.
        """
        if new_baseline:
            self.baseline = new_baseline

    def clear_secondary(self) -> None:
        """
        Reset secondary emotional shades.
        Typically called before recomputing them in the emotion engine.
        """
        self.secondary.clear()

    # ---- Serialization helpers -------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to a JSON-serializable dict.
        Useful for saving in Memory/state.json or session files.
        """
        data = asdict(self)
        # ensure everything is JSON-friendly (floats/strings/lists are fine)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionalState":
        """
        Restore emotional state from a dict.
        Missing fields fall back to defaults.
        """
        return cls(
            baseline=data.get("baseline", "curious"),
            mood=data.get("mood", "neutral"),
            primary=data.get("primary", "neutral"),
            secondary=list(data.get("secondary", [])),
            history=list(data.get("history", [])),
            last_update_ts=float(data.get("last_update_ts", time.time())),
            fusion=data.get("fusion"),  # optional, defaults to None
            last_fusion_update=float(data.get("last_fusion_update", time.time())),
        )


# ---- Small helpers --------------------------------------------------------


def create_default_state(baseline: str = "curious") -> EmotionalState:
    """
    Convenience function to create a fresh heart for Nova.

    You can call this at startup:
        emotional_state = create_default_state("quiet_warmth")
    """
    return EmotionalState(baseline=baseline)
