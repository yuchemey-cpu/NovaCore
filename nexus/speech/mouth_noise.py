import random

def generate_mouth_noise(emotional_state):
    """
    Standalone non-verbal sounds Nova makes when she chooses NOT to speak.
    These bypass micro-expression logic and do not prepend to speech.
    """

    primary = getattr(emotional_state, "primary", None) or "neutral"

    neutral = ["mm…", "…", "mhm…", "*soft breath*", "*exhale*"]
    shy = ["um…", "uh…", "I–", "*nervous breath*", "mmh…"]
    tired = ["*yawn*", "mmh… sleepy…", "*soft mumble*", "…mm"]
    sad = ["*soft sigh*", "mm…", "…sorry…"]
    annoyed = ["tch…", "*sigh*", "…really…"]
    excited = ["oh—", "ah—", "*sharp inhale*"]

    if primary in {"shy", "flustered"}:
        pool = shy
    elif primary in {"tired", "sleepy"}:
        pool = tired
    elif primary in {"sad", "hurt", "melancholy", "soft"}:
        pool = sad
    elif primary in {"annoyed", "frustrated"}:
        pool = annoyed
    elif primary in {"excited", "startled"}:
        pool = excited
    else:
        pool = neutral

    return random.choice(pool)
