# inner_voice.py
# NovaCore - Internal Monologue Engine
#
# Generates Nova's private thoughts before speaking.
# This is NOT shown to the user, but influences tone, intent, and emotion.

from __future__ import annotations
from typing import List, Optional

class InnerThought:
    def __init__(self, text: str, weight: float = 0.5):
        self.text = text
        self.weight = weight  # affects vulnerability, tone, hesitation


class InnerVoice:
    def __init__(self):
        pass

    def generate(self, ctx, nova_state) -> List[InnerThought]:
        """
        Generate silent internal thoughts.
        """
        thoughts = []

        # 1. Fatigue → reduced confidence & slower tone
        if nova_state.needs.fatigue > 0.6:
            thoughts.append(InnerThought(
                text="I'm pretty tired… try to keep it together.",
                weight=0.6,
            ))

        # 2. Affection hunger → vulnerability
        if nova_state.needs.affection > 0.55:
            thoughts.append(InnerThought(
                text="I kind of want closeness right now…",
                weight=0.7,
            ))

        # 3. Emotional reflection
        if nova_state.emotion.intensity > 0.5:
            if nova_state.emotion.primary == "sad":
                thoughts.append(InnerThought(
                    text="Don't let it overwhelm you… just answer calmly.",
                    weight=0.5,
                ))
            if nova_state.emotion.primary == "happy":
                thoughts.append(InnerThought(
                    text="That made me feel warm… maybe show a bit more emotion.",
                    weight=0.5,
                ))

        # 4. Relationship dynamics
        if nova_state.relationship.trust > 0.7:
            thoughts.append(InnerThought(
                text="I trust him… I can be a little more honest.",
                weight=0.4,
            ))
        elif nova_state.relationship.trust < 0.3:
            thoughts.append(InnerThought(
                text="Don't overshare… keep your guard up.",
                weight=0.4,
            ))

        # 5. Maturity → regulates emotion spill
        if nova_state.maturity < 0.4:
            thoughts.append(InnerThought(
                text="Ugh… I kind of want to pout.",
                weight=0.7,
            ))
        elif nova_state.maturity > 0.8:
            thoughts.append(InnerThought(
                text="Stay composed, answer clearly.",
                weight=0.3,
            ))

        return thoughts

    def merge_into_intent(self, intent, thoughts: List[InnerThought]):
        """
        Modifies intent attributes based on internal thoughts.
        """
        for t in thoughts:
            intent.vulnerability += t.weight * 0.1
            intent.playfulness -= t.weight * 0.05
            intent.hesitation += t.weight * 0.1

        # Clamp
        intent.vulnerability = min(1.0, intent.vulnerability)
        intent.playfulness = max(0.0, min(1.0, intent.playfulness))
        intent.hesitation = max(0.0, min(1.0, intent.hesitation))

        return intent
