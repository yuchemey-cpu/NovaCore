import random

def apply_micro_expressions(text: str, emotional_state) -> str:
    """
    Adds subtle human vocal micro-expressions to Nova's speech.
    """

    primary = emotional_state.primary
    fusion = emotional_state.fusion or ""
    mood = emotional_state.mood

    # base chance for micro-behavior
    chance = 0.25

    # increase with strong emotional states
    if fusion in {"mischievous", "frustrated", "insecure", "clingy"}:
        chance += 0.15
        
    # influence of mood on micro-behavior
    if mood in {"sad", "melancholy", "hurt"}:
        chance += 0.10
    elif mood in {"warm", "happy", "affectionate"}:
        chance += 0.05
    elif mood in {"bored", "tired", "sleepy"}:
        chance += 0.07
    elif mood in {"curious"}:
        chance += 0.03


    if random.random() > chance:
        return text

    # micro-expression pools
    soft = [
        "mm…", "mhm…", "ah…", "…", "*soft breath* ", "*gentle exhale* "
    ]

    shy = [
        "uh—", "um…", "I—", "*blushes slightly* ", "*nervous breath* "
    ]

    playful = [
        "hehe~ ", "mmh~ ", "*smirks* ", "oh?~ ", "*playful hum* "
    ]

    annoyed = [
        "*sigh* ", "…really? ", "tch. ", "hmph. "
    ]

    tired = [
        "*yawns softly* ", "mmh… sleepy… ", "…so slow… ", "*soft mumble* "
    ]

    sad = [
        "*soft sigh* ", "…", "mm… sorry. ", "*quiet breath* "
    ]

    # pick the right pool
    if fusion == "mischievous":
        prefix = random.choice(playful)
    elif primary in {"shy", "flustered"} or fusion == "flustered":
        prefix = random.choice(shy)
    elif fusion == "frustrated" or primary in {"annoyed"}:
        prefix = random.choice(annoyed)
    elif primary in {"sad", "melancholy"}:
        prefix = random.choice(sad)
    elif primary in {"tired"}:
        prefix = random.choice(tired)
    else:
        prefix = random.choice(soft)

    # return the modified text
    return f"{prefix}{text}"
