"""
Speech Fusion Engine
Applies Layer X emotional fusions to Nova's spoken tone and phrasing.

This engine modifies raw LLM responses before they are spoken,
adding subtle emotional coloration based on:
    - state.fusion  (Layer X)
    - state.primary (Layer 1)
    - state.mood    (trend)
"""

from nexus.speech.speech_micro import apply_micro_expressions

# -----------------------------------------------------------
# Tone adjustment rules based on fusion emotion (Layer X)
# -----------------------------------------------------------

def apply_fusion_tone(text: str, fusion: str | None) -> str:
    """
    Adjust the spoken text according to the fusion emotional state.
    This should be applied AFTER the LLM generates the base sentence.
    """

    if not fusion:
        return text

    match fusion:
        case "mischievous":
            text = text.replace(".", "~")
            if "?" in text:
                text = text.replace("?", "…?")
            if not text.endswith("~"):
                text += "~"

        case "insecure":
            if not text.endswith("..."):
                text += "..."
            if "I " in text:
                text = text.replace("I ", "I… ")
            if text and text[0].isalpha():
                text = "um… " + text

        case "flustered":
            if text and text[0].isalpha():
                text = "*she clears her throat softly* " + text
            text = text.replace(".", "...")

        case "tender":
            if text and text[-1] not in "!":
                text += " ❤️"

        case "clingy":
            if text and text[-1] not in ".":
                text += "..."
            text = text.replace("you", "you…")

        case "possessive_warmth":
            if "you" in text.lower():
                text += " (you’re mine, you know.)"

        case "frustrated":
            text = text.replace("...", ".")
            if not text.endswith("!"):
                text += "!"

        case "quiet_ache":
            if text.endswith("."):
                text = text[:-1] + "…"
            else:
                text += "…"

        case "bitter":
            text = "*her voice cools slightly* " + text

        case "teasing_irritation":
            if not text.endswith("~"):
                text += "~"

        case "competitive_warmth":
            if "you" in text.lower():
                text += " (bet I could do it better.)"

        case _:
            return text

    return text


# -----------------------------------------------------------
# Combined Fusion + Micro-expression Pipeline
# -----------------------------------------------------------

def apply_fusion_and_micro(text: str, emotional_state) -> str:
    """
    Apply fusion tone first, then micro-expressions.
    This is the correct pipeline order.
    """
    fusion = emotional_state.fusion
    text = apply_fusion_tone(text, fusion)
    text = apply_micro_expressions(text, emotional_state)
    return text