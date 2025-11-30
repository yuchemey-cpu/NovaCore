# Nova/Emotion/mood_engine.py

"""
Mood Engine – determines Nova's medium-term emotional mood
based on recent primary emotions.

Lightweight, stable, and game-safe.
"""

from collections import Counter
from typing import List


def calculate_mood(history: List[str]) -> str:
    """
    Determine mood from recent emotions.

    Rules:
    - If no history → neutral
    - If one emotion dominates → that emotion becomes mood
    - If emotions are mixed → return neutral for stability
    - Only emotions that appear at least 2 times count as mood
    """

    if not history:
        return "neutral"

    counts = Counter(history)
    (emotion, amount) = counts.most_common(1)[0]

    # Prevent mood thrashing (must appear at least twice)
    if amount < 2:
        return "neutral"

    return emotion
