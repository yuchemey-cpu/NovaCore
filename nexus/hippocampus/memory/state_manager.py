import json
import os
from nexus.amygdala.emotion.emotional_state import EmotionalState

SAVE_PATH = os.path.join("Memory", "data", "emotional_state.json")


def load_emotional_state() -> EmotionalState:
    """Load emotional state from disk, or create a new one."""
    if not os.path.exists(SAVE_PATH):
        # First launch or no save exists
        return EmotionalState()

    try:
        with open(SAVE_PATH, "r") as f:
            data = json.load(f)
        return EmotionalState.from_dict(data)

    except Exception as e:
        print(f"[StateManager] Failed to load emotional state: {e}")
        return EmotionalState()


def save_emotional_state(state: EmotionalState):
    """Save emotional state to disk."""
    try:
        os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
        with open(SAVE_PATH, "w") as f:
            json.dump(state.to_dict(), f, indent=2)
    except Exception as e:
        print(f"[StateManager] Failed to save emotional state: {e}")
