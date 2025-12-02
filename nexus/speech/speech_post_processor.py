# speech_post_processor.py
# NovaCore - post-processing layer for Nova's spoken text.
#
# This runs AFTER the LLM has produced a reply, and uses the Intent
# to add small speech micro-patterns (hesitations, pouts, soft sounds).
#
# It must NEVER change the meaning, only the flavour.

from __future__ import annotations

from typing import Optional
from nexus.cortex.thinking.intent_builder import Intent


class SpeechPostProcessor:
    """
    Lightweight speech decorator.
    - Adds tiny fillers like "mm...", "uh", "hmph" based on tone.
    - Softens or tightens phrases depending on vulnerability / playfulness.
    - This sits between LlmBridge and TTS/printing.
    """

    def __init__(self, enable_micro: bool = True):
        self.enable_micro = enable_micro

    def process(self, text: str, intent: Intent) -> str:
        """
        Main entry point.
        """
        if not self.enable_micro:
            return text

        cleaned = text.strip()

        # Very short or empty → don't touch much
        if len(cleaned) == 0:
            return cleaned
        if len(cleaned) < 4:
            return cleaned
        if intent.hesitation > 0.4:
            reply = "uh… " + reply


        # Apply tone-based tweaks
        if intent.tone_style == "pouty":
            cleaned = self._apply_pouty(cleaned, intent)
        elif intent.tone_style in ("soft", "gentle"):
            cleaned = self._apply_soft(cleaned, intent)
        elif intent.tone_style in ("hesitant", "light"):
            cleaned = self._apply_hesitant(cleaned, intent)
        elif intent.tone_style == "flat":
            cleaned = self._apply_flat(cleaned, intent)
        else:
            # default calm kuudere – occasionally a tiny "mm" or "ah"
            cleaned = self._apply_kuudere(cleaned, intent)

        return cleaned

    # ---------------------------------------------------------
    # Tone helpers
    # ---------------------------------------------------------

    def _apply_pouty(self, text: str, intent: Intent) -> str:
        # Add a subtle pout in the front if not already starting with something like "..."
        prefix = ""
        if not text.startswith(("…", ".", "mm", "uh", "hmph")):
            prefix = "…"
        # Occasionally add a little "hmph" at the end for medium-length lines.
        if 15 < len(text) < 120:
            if not text.endswith((".", "!", "?", "…")):
                text = text + "..."
            text = text + " hmph."
        return prefix + text

    def _apply_soft(self, text: str, intent: Intent) -> str:
        # For soft / gentle moods, prepend a tiny "mm" or "mhmm" sometimes.
        if not text.lower().startswith(("mm", "mhmm", "uh", "ah", "well")):
            # Higher vulnerability → more likely to start with a soft hesitation
            if intent.vulnerability > 0.5:
                return "mm… " + text
        return text

    def _apply_hesitant(self, text: str, intent: Intent) -> str:
        # Hesitant tone: maybe start with "uh" or "I..." if appropriate.
        lowered = text.lower()
        if lowered.startswith(("i ", "i'm", "i am")):
            # Slight stutter / hesitation
            return "I… " + text[2:] if lowered.startswith("i ") else "I… " + text[1:]
        if not text.lower().startswith(("uh", "um", "well")):
            return "uh… " + text
        return text

    def _apply_flat(self, text: str, intent: Intent) -> str:
        # Flat tone: minimal decoration – maybe remove exclamation spam.
        if "!!" in text:
            text = text.replace("!!", ".")
        return text

    def _apply_kuudere(self, text: str, intent: Intent) -> str:
        # Default calm/kuudere. Very small chance to add a soft "mm".
        if intent.playfulness > 0.6 and not text.lower().startswith(("mm", "ah", "uh")):
            return "mm… " + text
        return text
