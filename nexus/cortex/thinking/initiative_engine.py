# initiative_engine.py
# NovaCore - Initiative Engine
#
# Determines when Nova should start or extend a conversation on her own.

from __future__ import annotations
import random
from typing import Optional

class InitiativeIntent:
    def __init__(self, content: str, priority: float = 0.5):
        self.content = content
        self.priority = priority    # 0–1 (higher = stronger override)


class InitiativeEngine:
    def __init__(self):
        self.cooldown = 0          # turns before next initiative allowed

    def evaluate(self, nova_state, ctx) -> Optional[InitiativeIntent]:
        """
        Evaluate whether Nova wants to initiate a topic.
        Returns InitiativeIntent or None.
        """

    # If user is already asking something → no initiative
        if hasattr(nova_state, "last_user_message"):
            last_msg = nova_state.last_user_message or ""
            if "?" in last_msg:
                return None
        
        if ctx.is_direct_question:
            return None


        # Cooldown: prevents spamming initiative
        if self.cooldown > 0:
            self.cooldown -= 1
            return None

        pressure = nova_state.needs.pressure
        trust = nova_state.relationship.trust
        affection = nova_state.needs.affection
        fatigue = nova_state.needs.fatigue
        emotion = nova_state.emotion.primary

        # BASE CHANCE
        chance = 0.1

        # HIGH AFFECTION → wants to talk
        if affection > 0.55:
            chance += 0.2

        # HIGH EMOTION → wants to express
        if nova_state.emotion.intensity > 0.6:
            chance += 0.15

        # HIGH TRUST → more opening up
        if trust > 0.6:
            chance += 0.1

        # FATIGUE → less initiative
        if fatigue > 0.6:
            chance -= 0.15

        # VERY LOW TRUST → no initiative
        if trust < 0.25:
            return None

        # Final decision
        if random.random() > chance:
            return None

        # Choose message
        message = self._choose_topic(nova_state)
        if not message:
            return None

        # Set cooldown so she doesn't spam
        self.cooldown = random.randint(3, 8)

        return InitiativeIntent(content=message, priority=chance)

    def _choose_topic(self, state):
        """
        Pick what Nova wants to talk about.
        """

        # Emotional expression
        if state.needs.affection > 0.6:
            return "Hey… can I ask you something?"

        if state.mood.valence > 0.4:
            return "So um… what are you doing right now?"

        if state.mood.valence < -0.3:
            return "Mmm… it's been a weird day."

        if state.needs.fatigue > 0.7:
            return "*yawn* …how are you?"

        # Fall back
        return "Hey…"
