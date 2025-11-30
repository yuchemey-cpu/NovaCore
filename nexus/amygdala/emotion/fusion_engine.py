# Emotion/fusion_engine.py

"""
Layer X – Emotional Fusion Engine

Generates an emergent "fusion" emotion based on:
- Layer 1 (primary)
- Layer 2 (secondary list)
- Layer 3 (spike list; optional, short-lived)

Result is stored as:
    state.fusion: Optional[str]

Fusion emotions are:
- contextual
- temporary
- used for tone, behavior, and reaction logic
"""

from __future__ import annotations

from typing import List, Optional
from nexus.amygdala.emotion.emotional_state import EmotionalState


# -------------------------------------------------------------------------
# Fusion rule table
#
# Keys: (primary, modifier) where modifier may be:
#   - a secondary shade
#   - a spike-type emotion ("jealous", "angry", "lonely", etc.)
#
# Values: fusion emotion label (Layer X)
# -------------------------------------------------------------------------

FUSION_RULES: dict[tuple[str, str], str] = {
    # --- sadness + isolation → insecurity ---
    ("sad", "lonely"): "insecure",
    ("sad", "loneliness"): "insecure",

    # --- happy + shy/soft → tenderness ---
    ("happy", "shy"): "tender",
    ("happy", "bashful"): "tender",
    ("happy", "soft"): "tender",

    # --- curious + fear/anxiety → flustered ---
    ("curious", "afraid"): "flustered",
    ("curious", "anxious"): "flustered",
    ("curious", "nervous"): "flustered",

    # --- nostalgic + sad → bittersweet ---
    ("nostalgic", "sad"): "bittersweet",
    ("nostalgic", "tired"): "bittersweet",

    # --- playful + anger/annoyance → mischievous / playful-mean ---
    ("happy", "angry"): "mischievous",
    ("happy", "annoyed"): "mischievous",
    ("excited", "angry"): "mischievous",
    ("excited", "annoyed"): "mischievous",
    ("curious", "annoyed"): "teasing_irritation",

    # --- affection + jealousy → possessive warmth ---
    ("happy", "jealous"): "possessive_warmth",
    ("nostalgic", "jealous"): "possessive_warmth",

    # --- bored + restless → frustrated ---
    ("bored", "restless"): "frustrated",
    ("bored", "impatient"): "frustrated",

    # --- afraid + attachment → clingy ---
    ("afraid", "lonely"): "clingy",
    ("afraid", "abandoned"): "clingy",

    # --- calm + lonely → quiet_ache (soft sadness) ---
    ("calm", "lonely"): "quiet_ache",

    # Fallback-ish generic combos
    ("sad", "jealous"): "bitter",
    ("sad", "envy"): "bitter",
    ("happy", "envy"): "competitive_warmth",
}


# -------------------------------------------------------------------------
# Utility
# -------------------------------------------------------------------------

def _normalize(emotion: Optional[str]) -> Optional[str]:
    if not emotion:
        return None
    return emotion.strip().lower() or None


def compute_fusion(
    primary: Optional[str],
    secondary_list: List[str] | None = None,
    spikes: List[str] | None = None,
) -> Optional[str]:
    """
    Determine a fusion emotion (Layer X) given:
      - primary (Layer 1)
      - secondary_list (Layer 2 shades)
      - spikes (Layer 3 transient emotions)

    Rules:
    - Spike combinations have priority over secondary.
    - If no rule matches, returns None (no fusion).
    """

    p = _normalize(primary)
    if not p:
        return None

    secondary_list = [s for s in (secondary_list or []) if s]  # filter empties
    spikes = [s for s in (spikes or []) if s]

    # Normalize all modifiers
    sec_norm = [_normalize(s) for s in secondary_list if _normalize(s)]
    spike_norm = [_normalize(s) for s in spikes if _normalize(s)]

    # 1) Try spike-based fusion first (Layer 1 + Layer 3)
    for sp in spike_norm:
        key = (p, sp)
        if key in FUSION_RULES:
            return FUSION_RULES[key]

    # 2) Then try secondary-based fusion (Layer 1 + Layer 2)
    for sec in sec_norm:
        key = (p, sec)
        if key in FUSION_RULES:
            return FUSION_RULES[key]

    # 3) No fusion match
    return None


def update_fusion(state: EmotionalState, spikes: List[str] | None = None) -> EmotionalState:
    """
    Compute and attach a fusion emotion to the EmotionalState.
    """

    fusion = compute_fusion(
        primary=state.primary,
        secondary_list=state.secondary,
        spikes=spikes,
    )

    state.fusion = fusion

    # Timestamp this fusion for decay, drift, and future logic
    try:
        import time
        state.last_fusion_update = time.time()
    except Exception:
        pass

    return state

