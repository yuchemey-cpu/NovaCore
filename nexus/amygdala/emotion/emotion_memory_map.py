import json
import os
import time

# Correct file path for your new architecture
MAP_PATH = os.path.join("..", "Memory", "data", "emotion_memory_map.json")


def load_map():
    """Load the emotional memory map from disk."""
    try:
        if not os.path.exists(MAP_PATH):
            return {}
        with open(MAP_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}  # fail-safe


def save_map(memory_map):
    """Save the emotional memory map to disk."""
    os.makedirs(os.path.dirname(MAP_PATH), exist_ok=True)
    with open(MAP_PATH, "w") as f:
        json.dump(memory_map, f, indent=2)


def get_emotion(memory_map, stimulus):
    """Return stored emotion or None."""
    entry = memory_map.get(stimulus.lower())
    if entry:
        return entry.get("emotion", "neutral")
    return None


def update_emotion(memory_map, stimulus, new_emotion, reinforce=0):
    """
    Update or reinforce emotion for a stimulus.
    This version includes:
    - reinforcement score
    - count of occurrences
    - last-seen timestamp
    """
    stimulus = stimulus.lower()

    # Retrieve or create new entry
    entry = memory_map.get(stimulus, {
        "emotion": new_emotion,
        "reinforcement": 0,
        "count": 0,
        "last_seen": time.time()
    })

    # Update reinforcement
    entry["reinforcement"] += reinforce

    # Count how many times this thing appeared
    entry["count"] += 1

    # Update timestamp
    entry["last_seen"] = time.time()

    # Reinforcement logic
    if reinforce < 0 and entry["reinforcement"] <= -2:
        entry["emotion"] = "afraid"
    elif reinforce > 0 and entry["reinforcement"] >= 2:
        entry["emotion"] = new_emotion

    # Save entry back
    memory_map[stimulus] = entry
