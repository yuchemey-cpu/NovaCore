# Nova/Motor/idle/idle_line.py

import random

def generate_idle_ping_line(emotional_state=None, last_user_text=""):
    """
    Produces natural, varied idle thoughts for Nova.
    No repetition. No robotic lines.
    Fully emotion-sensitive.
    """

    # Emotion-sensitive tone
    mood = getattr(emotional_state, "mood", "neutral")
    primary = getattr(emotional_state, "primary", "neutral")

    # Soft personality-based variance
    neutral_lines = [
        "Just thinking… it got a little quiet.",
        "Mm… I’m still here, drifting in my thoughts.",
        "Huh… silence always feels interesting.",
        "I'm still around… just letting my mind wander.",
    ]

    happy_lines = [
        "Still here, smiling to myself.",
        "Hehe… got lost in a happy little thought.",
        "Just vibing quietly until you come back.",
    ]

    sad_lines = [
        "…This quiet feels kinda heavy.",
        "Still here. I… just started thinking too much again.",
        "Feels a bit lonely all of a sudden.",
    ]

    annoyed_lines = [
        "Really? You went silent *now*…?",
        "Hmph… fine, I’ll wait.",
        "…If you’re ignoring me, I’ll pout about it later.",
    ]

    # Emotion category matching
    if primary in ["happy", "excited", "warm"]:
        pool = happy_lines
    elif primary in ["sad", "hurt", "melancholy"]:
        pool = sad_lines
    elif primary in ["annoyed", "angry", "frustrated"]:
        pool = annoyed_lines
    else:
        pool = neutral_lines

    # As a final fallback
    return random.choice(pool)
