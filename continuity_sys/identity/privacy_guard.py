# Identity/privacy_guard.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class PrivacyState:
    # How many times in a row the user pushed on a private topic
    consecutive_attempts: int = 0

    # Total number of pushes this session (used for hybrid behavior)
    total_attempts: int = 0

    # If True, Nova should stay silent on this topic until apology / subject change
    hard_locked: bool = False

    # Last time a privacy probe happened (for decay)
    last_attempt_time: float = 0.0

    # Rough tag of what they were asking about ("she", "friend", etc)
    last_topic_tag: str = ""

    # Whether user has recently apologized / backed off
    recently_forgiven: bool = False


class PrivacyGuard:
    """
    Handles:
    - Detecting when the user is prying about someone else / private info
    - Escalating responses: soft → firmer → warning → silence
    - Releasing the 'lock' when the user apologizes or changes subject
    Hybrid mode:
      - consecutive_attempts escalates quickly for this topic
      - total_attempts makes her a bit less tolerant if it keeps happening all session
    """

    def __init__(self):
        self.state = PrivacyState()

        # Phrases can later be emotion-aware; for now they’re neutral-soft
        self._soft_lines = [
            "Sorry, Yuch… I shouldn’t say. She was kind enough to share that with me, and I don’t want to break that.",
            "Mmm… I can’t really talk about that. It doesn’t feel right.",
        ]

        self._firm_lines = [
            "Yuch… please don’t push me on this. I really don’t want to break someone’s trust.",
            "Hey… I said I can’t talk about that. Don’t make me repeat it.",
        ]

        self._warning_lines = [
            "Yuch. If you pry one more time about this, I’m going to stop talking about it.",
            "I mean it, Yuch. One more push and I’m done with this topic.",
        ]

        # What she says after you apologize / back off
        self._forgive_lines = [
            "…Thank you. I just didn’t want to lose that bond. Let’s talk about something else instead.",
            "That’s better. Let’s drop it and move on, okay?",
        ]

    # ------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------
    def on_user_turn(self, user_text: str) -> None:
        """
        Called every user message so we can:
        - detect apologies
        - detect topic change
        - decay escalation a bit over time
        """
        lowered = user_text.strip().lower()

        # If they apologize or promise to stop prying → reset lock
        if any(word in lowered for word in ["sorry", "i won't pry", "i wont pry", "i’ll stop", "i will stop"]):
            self._reset_after_apology()
            return

        # If this turn is not a privacy probe, we may reduce consecutive_attempts slowly
        if not self._looks_like_privacy_probe(lowered):
            # Topic changed: decay the streak
            if self.state.consecutive_attempts > 0:
                self.state.consecutive_attempts -= 1
                if self.state.consecutive_attempts <= 0:
                    self.state.consecutive_attempts = 0
            # If they move on long enough, unlock hard lock too
            if self.state.consecutive_attempts == 0:
                self.state.hard_locked = False
            return

    def maybe_block_request(self, user_text: str, emotion_primary: Optional[str] = None) -> Optional[str]:
        """
        Called from LlmBridge BEFORE generating a normal reply.
        If this returns a string → send that instead of the usual reply.
        If it returns None -> safe, continue as normal.
        """
        text = user_text.strip().lower()

        # Already in hard lock on this topic → silence / ellipsis
        if self.state.hard_locked and self._looks_like_privacy_probe(text):
            # She refuses to talk until subject changes or apology happens
            return "..."

        # If this isn't a privacy probe, do nothing
        if not self._looks_like_privacy_probe(text):
            return None

        # Register the attempt and decide how to answer
        self._register_attempt(text)

        lvl = self.state.consecutive_attempts

        # Hybrid: if they’ve done this many times session-wide, escalate a bit faster
        session_factor = 1 if self.state.total_attempts < 5 else 2

        if lvl <= 1:
            # soft response
            return self._pick_soft_line(emotion_primary)
        elif lvl == 2 or (lvl == 1 and session_factor > 1):
            # firmer
            return self._pick_firm_line(emotion_primary)
        elif lvl == 3:
            # Warning
            return self._pick_warning_line(emotion_primary)
        else:
            # Lock it: one more and she goes silent
            self.state.hard_locked = True
            return "..."

    # ------------------------------------------------------
    # Internals
    # ------------------------------------------------------
    def _looks_like_privacy_probe(self, text: str) -> bool:
        """
        Very simple heuristic for now:
        - asking what someone else said
        - asking what she was told by 'him/her/them'
        We'll refine later if needed.
        """
        triggers = [
            "what did she say",
            "what did he say",
            "what did they say",
            "tell me what she said",
            "tell me what he said",
            "tell me what they said",
            "what can you tell me about what she said",
            "what can you tell me about what he said",
            "did someone tell you",
            "did anybody tell you",
            "what did you talk about with",
            "what did you two talk about",
        ]
        return any(t in text for t in triggers)

    def _register_attempt(self, text: str) -> None:
        self.state.consecutive_attempts += 1
        self.state.total_attempts += 1
        self.state.last_attempt_time = time.time()
        # rough topic tag
        if "she" in text:
            self.state.last_topic_tag = "she"
        elif "he" in text:
            self.state.last_topic_tag = "he"
        else:
            self.state.last_topic_tag = "other"

    def _reset_after_apology(self) -> None:
        self.state.consecutive_attempts = 0
        self.state.hard_locked = False
        self.state.recently_forgiven = True

    # ------------------------------------------------------
    # Line pickers (later can be emotion-aware)
    # ------------------------------------------------------
    def _pick_soft_line(self, emotion: Optional[str]) -> str:
        # Later: adjust by emotion. For now just pick the first.
        return self._soft_lines[0]

    def _pick_firm_line(self, emotion: Optional[str]) -> str:
        return self._firm_lines[0]

    def _pick_warning_line(self, emotion: Optional[str]) -> str:
        return self._warning_lines[0]

    def pick_forgive_line(self) -> str:
        return self._forgive_lines[0]
