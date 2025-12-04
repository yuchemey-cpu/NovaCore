# Nova/Emotion/emotion_engine.py

"""
EmotionalEngine – merged & evolved v2 system.

This replaces the old emotion_core.py while reusing:
- emotional memory map
- reinforcement learning
- keyword emotion detection
- fear avoidance
- mood drift

And integrates smoothly with:
- EmotionalState (Nova's heart)
"""

import random
from typing import Any, Dict

from nexus.amygdala.emotion.emotional_state import EmotionalState
from nexus.amygdala.emotion import fusion_engine
import nexus.amygdala.emotion.emotion_memory_map as emotion_memory_map
from nexus.amygdala.emotion.mood_engine import calculate_mood

# -----------------------------------------------------------------------------------
# Emotion keyword map (from your old system)
# -----------------------------------------------------------------------------------

EMOTION_KEYWORDS = {
    "happy": ["smile", "orange", "fun", "sun", "good"],
    "nostalgic": ["drawing", "duck", "memory", "paper", "old", "rain"],
    "curious": ["what", "why", "how", "unknown", "new", "mystery"],
    "excited": ["game", "win", "yay", "party", "start"],
    "bored": ["nothing", "wait", "blank", "idle"],
    "afraid": ["glass", "sharp", "danger", "hurt", "pain", "blood"],
    "sad": ["broken", "lost", "goodbye", "crack", "forgot", "gone"],
    "neutral": []
}


# -----------------------------------------------------------------------------------
# Load persistent emotional memory map
# -----------------------------------------------------------------------------------

emotion_map = emotion_memory_map.load_map()


# -----------------------------------------------------------------------------------
# Avoidance rule (fear reinforcement)
# -----------------------------------------------------------------------------------

def is_avoided(map_data: Dict[str, Any], stimulus: str, threshold: int = -2) -> bool:
    """If reinforcement indicates repeated fear, avoid this input."""
    if stimulus in map_data:
        fear_score = map_data[stimulus].get("afraid", 0)
        return fear_score <= threshold
    return False


# -----------------------------------------------------------------------------------
# Main emotional update logic
# -----------------------------------------------------------------------------------

def update_emotional_state(
    state: EmotionalState,
    heard_text: str,
    seen_text: str = ""
) -> EmotionalState:
    """
    Computes Nova's emotional reaction to new sensory/stimulus input.
    Updates EmotionalState accordingly.
    """

    stimulus = f"{heard_text.strip().lower()} {seen_text.strip().lower()}".strip()

    # -------------------------
    # 1) Fear avoidance
    # -------------------------
    if is_avoided(emotion_map, stimulus):
        # Strong fear memory detected
        state.push_emotion("afraid")
        state.mood = "afraid"
        state.secondary = ["alert", "cautious"]
        return state

    # -------------------------
    # 2) Recall previous association
    # -------------------------
    remembered = emotion_memory_map.get_emotion(emotion_map, stimulus)
    if remembered:
        # Reinforce memory if same emotion reoccurs
        emotion_memory_map.update_emotion(
            emotion_map, stimulus, remembered, reinforce=+1
        )
        primary = remembered
    else:
        # -------------------------
        # 3) Keyword scoring
        # -------------------------
        scores = {e: 0 for e in EMOTION_KEYWORDS}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for word in keywords:
                if word in stimulus:
                    scores[emotion] += 1

        # add light continuity
        if state.primary in scores:
            scores[state.primary] += 0.5

        # choose best match or fall back
        primary = max(scores, key=scores.get)
        if scores[primary] == 0:
            primary = random.choice(["curious", "neutral"])

        # Save first-time emotional association
        emotion_memory_map.update_emotion(
            emotion_map, stimulus, primary, reinforce=0
        )

    # -------------------------
    # 4) Update primary emotion
    # -------------------------
    state.push_emotion(primary)

    # -------------------------
    # 5) Recompute mood
    # -------------------------
    state.mood = calculate_mood(state.history)


    # -------------------------
    # 6) Compute secondary shades
    # -------------------------
    SECONDARY_MAP = {
        "happy": ["curious", "excited"],
        "nostalgic": ["sad", "warm"],
        "curious": ["neutral", "hopeful"],
        "afraid": ["alert", "cautious"],
        "sad": ["nostalgic", "tired"],
        "bored": ["blank", "restless"],
        "excited": ["happy", "eager"],
        "neutral": [],
    }

    combined = set()
    combined.update(SECONDARY_MAP.get(primary, []))
    combined.update(SECONDARY_MAP.get(state.mood, []))
    combined.update(SECONDARY_MAP.get(state.baseline, []))

    state.secondary = [e for e in combined if e not in (primary, state.mood)]

    # -------------------------
    # 7) Layer X – fusion emotion
    # -------------------------
    try:
        # For now we don't pass explicit spikes; those can be added later
        # (e.g. jealousy, embarrassment) by higher-level systems.
        
        fusion_engine.update_fusion(state, spikes=None)
    except Exception:
        # Fail-safe: fusion is purely cosmetic; never break core logic.
        pass

    return state

class EmotionEngine:
    def __init__(self, state=None):
        self.state = state or EmotionalState()

    def detect_user_emotion(self, text):
        return update_emotional_state(self.state, text)

    def update(self, emotional_input):
        self.state = emotional_input
        return self.state


# -----------------------------------------------------------------------------------
# Save emotional map at shutdown
# -----------------------------------------------------------------------------------

def save_emotion_map():
    emotion_memory_map.save_map(emotion_map)

