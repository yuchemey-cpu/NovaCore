# nova_state.py
# NovaCore - Unified NovaState
#
# This module defines a persistent snapshot of Nova's internal state
# across turns. It acts as a shared structure between BrainLoop,
# IntentBuilder, and other engines.

from __future__ import annotations

from typing import Any, Optional

from dataclasses import dataclass, field
from typing import List, Optional

from nexus.cortex.thinking.intent_builder import (
    EmotionSnapshot,
    MoodSnapshot,
    NeedsSnapshot,
    RelationshipSnapshot,
    MemorySnippet,
)


@dataclass
class NovaState:
    """Persistent internal state for Nova.

    This is *not* sent to the LLM. It lives entirely in NovaCore and is
    updated by BrainLoop each turn.
    """

    # Core emotional & cognitive state
    emotion: EmotionSnapshot = field(default_factory=EmotionSnapshot)
    mood: MoodSnapshot = field(default_factory=MoodSnapshot)
    needs: NeedsSnapshot = field(default_factory=NeedsSnapshot)
    relationship: RelationshipSnapshot = field(default_factory=RelationshipSnapshot)

    maturity: float = 0.5          # 0.0–1.0, from MaturityEngine
    persona_brief: str = ""        # short summary from PersonaEngine

    # Memory
    recent_memory: List[MemorySnippet] = field(default_factory=list)
    episodic_memory: List[MemorySnippet] = field(default_factory=list)

    # Dialogue context
    last_user_message: Optional[str] = None
    last_nova_reply: Optional[str] = None
    drive: Optional[Any] = None


    # Meta
    turn_count: int = 0

    def update_turn(
    self,
    user_message: str,
    new_emotion: EmotionSnapshot,
    new_mood: MoodSnapshot,
    new_needs: NeedsSnapshot,
    new_relationship: RelationshipSnapshot,
    maturity: float,
    persona_brief: str,
    recent_memory: List[MemorySnippet],
    episodic_memory: List[MemorySnippet],
    new_drive: Optional[Any] = None,
) -> None:

         

        """Update Nova's state at the start of a new turn."""

        self.turn_count += 1

        self.last_user_message = user_message
        self.emotion = new_emotion
        self.mood = new_mood
        self.needs = new_needs
        self.relationship = new_relationship

        self.maturity = maturity
        self.persona_brief = persona_brief

        self.recent_memory = recent_memory
        self.episodic_memory = episodic_memory
        
        self.drive = new_drive


    def record_reply(self, reply: str) -> None:
        """Store the last thing Nova said for continuity/reflection."""
        self.last_nova_reply = reply
