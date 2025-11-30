import datetime
import time
import requests
import random
import re

from core.base_module import NovaModule

from nexus.hippocampus.memory.state_manager import load_emotional_state
from nexus.hippocampus.memory.memory_engine import MemoryEngine
from nexus.hippocampus.memory.config import MEMORY_FILE, SESSIONS_DIR
from nexus.hippocampus.memory.memory_library.tools import MemoryLibrary

from nexus.amygdala.emotion import emotion_engine
from nexus.amygdala.emotion.mood_engine import calculate_mood
from nexus.amygdala.emotion.emotional_state import EmotionalState, create_default_state

from brainstem.drive.drive_engine import DriveEngine

from nexus.speech.speech_fusion import apply_fusion_and_micro
from nexus.speech.mouth_noise import generate_mouth_noise

from nexus.cortex.persona.persona_engine import PersonaEngine

from continuity_sys.continuity.continuity_engine import ContinuityEngine

from continuity_sys.identity.identity_engine import IdentityEngine
from continuity_sys.identity.privacy_guard import PrivacyGuard


class LlmBridge(NovaModule):
    """
    Conversation core.

    Handles:
    - USER_TEXT events
    - Emotional + mood updates
    - Persona updates
    - Memory updates
    - Building context for the LLM
    - Calling local LLM
    - Speech fusion (tone, micro)
    - Emitting NOVA_SPEAK replies

    This is also where we are starting to add a
    'conversation governor' so Nova can eventually
    decide *when* to speak, not just *what* to say.
    """

    def __init__(
        self,
        use_local_llm: bool = True,
        fast_model: str = "llama3.1:8b",
        deep_model: str = "llama3.1:8b",
        memory_engine: MemoryEngine | None = None,
        continuity_engine: ContinuityEngine | None = None,
        memory_library: MemoryLibrary | None = None,
    ):
        super().__init__("llm_bridge")

        # LLM configuration
        self.use_local_llm = use_local_llm
        self.fast_model = fast_model
        self.deep_model = deep_model

        # Legacy systems (kept for compatibility)
        self.memory_engine = memory_engine
        self.continuity_engine = continuity_engine

        # NEW unified human-like memory system
        self.memory_library = memory_library

        # NEW identity engine (relationship / I vs We)
        # Starts as "acquaintance": I=100%, We=0%
        self.identity = IdentityEngine(default_stage="acquaintance")

        # Persona system
        self.persona_engine = PersonaEngine()

        # Privacy guard
        self.privacy_guard = PrivacyGuard()

        # Soft idle/noise output flag
        self._is_noise_output = False

        # Emotional state
        self.emotional_state: EmotionalState | None = load_emotional_state()
        if self.emotional_state is None:
            self.emotional_state = create_default_state()

        # Drive system
        self.drive_engine = DriveEngine()

        # Short-term text buffer (local conversation history)
        self.memory_buffer: list[str] = []
        self.max_memory = 10

        # Episodic staging
        self._pending_episodic: str | None = None
        self._last_episodic_ts: float = 0.0

        # Last mentioned external people (for simple "we" resolution)
        self.last_people: list[str] = []
        self._last_people_timestamp: float = 0.0
        self.last_people_timeout: float = 120.0  # seconds

        # --- Conversation governor state (foundation) ---
        self.last_user_time: float | None = None
        self.last_nova_time: float | None = None
        self.spontaneous_cooldown_until: float = 0.0
        # Later we'll add: user_emotion_hint, pending_urgent_thought, etc.

    # -------------------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------------------

    def on_event(self, event_type: str, data: dict):

        # ------------------------
        # USER TEXT
        # ------------------------
        if event_type == "USER_TEXT":
            return self._handle_user_text(data)

        # ------------------------
        # TIME ENGINE idle/sleep/dream speech
        # ------------------------
        if event_type == "TIMEENGINE_IDLE_SPEAK":
            text = data.get("text", "")
            return self._handle_idle_text(text)

        if event_type == "TIMEENGINE_SLEEP_SPEAK":
            text = data.get("text", "")
            return self._handle_sleep_text(text)

        if event_type == "TIMEENGINE_DREAM_SPEAK":
            text = data.get("text", "")
            return self._handle_dream_text(text)

    # -------------------------------------------------------------------------
    # CONVERSATION GOVERNOR (foundation)
    # -------------------------------------------------------------------------

    def can_nova_speak(self, reason: str = "reply", importance: float = 0.5) -> bool:
        """
        Basic first version of the speak governor.

        For now:
        - Always allow direct replies to user text.
        - This will later grow to include:
          A) reason check
          B) necessity check
          C) emotional impact check
          D) expression choice (speech vs mouth noise).
        """
        if reason == "reply":
            return True

        # For non-reply reasons (idle, spontaneous, etc.),
        # we'll start conservative and refine later.
        now = time.time()

        # If user just spoke very recently, avoid butting in.
        if self.last_user_time is not None and (now - self.last_user_time) < 2.0:
            return False

        # Placeholder: we can refine using 'importance' later.
        return True

    # -------------------------------------------------------------------------
    # REALISTIC SPEECH TIMING
    # -------------------------------------------------------------------------

    def _get_speech_delay(self, context: str = "reply", is_noise: bool = False) -> float:
        """
        Returns a realistic delay before Nova speaks based on emotion + situation.
        """
        primary = getattr(self.emotional_state, "primary", None) or "neutral"

        # Base delay by context
        if context == "reply":
            base = 0.18
        elif context == "idle":
            base = 0.25
        elif context == "sleep":
            base = 1.5
        elif context == "dream":
            base = 1.0
        else:
            base = 0.20

        # Emotion adjustments
        if primary in {"tired", "sleepy"}:
            base += 0.4
        elif primary in {"sad", "hurt", "melancholy", "soft"}:
            base += 0.25
        elif primary in {"shy", "flustered"}:
            base += 0.20
        elif primary in {"happy", "curious", "warm"}:
            base -= 0.03
        elif primary in {"excited", "startled"}:
            base -= 0.08
        elif primary in {"annoyed", "frustrated"}:
            base -= 0.05

        # Random human jitter
        if context in {"sleep", "dream"}:
            base += random.uniform(-0.2, 0.5)
        else:
            base += random.uniform(-0.05, 0.12)

        # Don't go below 50ms
        base = max(0.05, base)

        # Prevent her from talking again too fast after herself
        now = time.time()
        if self.last_nova_time is not None:
            if context == "reply":
                min_gap = 0.25
            elif context == "idle":
                min_gap = 0.40
            elif context == "sleep":
                min_gap = 0.80
            elif context == "dream":
                min_gap = 0.70
            else:
                min_gap = 0.30

            since_last = now - self.last_nova_time
            if since_last < min_gap:
                base += (min_gap - since_last)

        # Noise is slightly faster
        if is_noise:
            base *= 0.9

        return base

    # -------------------------------------------------------------------------
    # SPEECH EMISSION
    # -------------------------------------------------------------------------

    def _emit_speech(self, text: str, context: str = "reply"):
        """
        Emits normal speech (goes through micro-expressions etc.).
        """
        delay = self._get_speech_delay(context=context, is_noise=False)
        if delay > 0:
            time.sleep(delay)

        if self.core:
            self.last_nova_time = time.time()
            self.core.emit("NOVA_SPEAK", {"reply": text})

    # -------------------------------------------------------------------------
    # NOISE EMISSION
    # -------------------------------------------------------------------------

    def _emit_noise(self, noise: str, context: str = "idle"):
        """
        Emits a noise-only output that bypasses micro-expressions.
        """
        self._is_noise_output = True

        delay = self._get_speech_delay(context=context, is_noise=True)
        if delay > 0:
            time.sleep(delay)

        if self.core:
            self.last_nova_time = time.time()
            self.core.emit("NOVA_SPEAK", {"reply": noise})

    # -------------------------------------------------------------------------
    # TIME ENGINE HANDLERS
    # -------------------------------------------------------------------------

    def _handle_user_text(self, data: dict):
        raw_text = data.get("text", "")
        self.last_user_time = time.time()

        # Let privacy guard see every user turn (for apology / topic change)
        if hasattr(self, "privacy_guard") and self.privacy_guard:
            self.privacy_guard.on_user_turn(raw_text)

        clean_text, mode, model_name = self.select_mode(raw_text)

        # ---------------------------------------------------------------------
        # SIMPLE "WE" PRONOUN RESOLUTION (NO EMOTION LOGIC)
        # ---------------------------------------------------------------------
        res = self.resolve_we(clean_text)
        if res is None:
            # Unclear "we" usage -> ask and stop processing
            lower = clean_text.lower()
            if "we " in lower or lower.startswith("we"):
                if self.core:
                    self._emit_speech("When you say 'we', who do you mean?", context="reply")
                return
        # res == "nova" or "other" -> just continue normally

        # Emotion
        self.emotional_state = emotion_engine.update_emotional_state(
            self.emotional_state,
            clean_text,
        )

        # Mood
        try:
            self.emotional_state.mood = calculate_mood(self.emotional_state.history)
        except Exception:
            pass

        # Persona
        self.active_persona = self.persona_engine.get_persona_brief(self.emotional_state)

        # --- PRIVACY GUARD CHECK BEFORE NORMAL REPLY ---
        privacy_override = None
        if hasattr(self, "privacy_guard") and self.privacy_guard:
            primary = getattr(self.emotional_state, "primary", None)
            privacy_override = self.privacy_guard.maybe_block_request(
                clean_text,
                emotion_primary=primary,
            )

        if privacy_override is not None:
            # She answers with a boundary instead of a normal reply
            if self.core and self.can_nova_speak(reason="reply"):
                self._emit_speech(privacy_override, context="reply")
            return

        # Memory intake (short-term + semantic + emotional + episodic staging)
        self.remember(clean_text)

        # Generate reply
        reply = self.generate_reply(clean_text, mode, model_name)

        # Governor
        if self.core and self.can_nova_speak(reason="reply"):
            self._emit_speech(reply, context="reply")

        # After responding, consider turning this moment into an episodic memory
        self._commit_episodic_if_meaningful()

    # Handle idle speech
    def _handle_idle_text(self, text: str):
        if not self.evaluate_interrupt("idle", text):
            return
        self._emit_noise(text)

    # Handle sleep speech
    def _handle_sleep_text(self, text: str):
        if not self.evaluate_interrupt("sleep", text):
            return
        self._emit_noise(text)

    # Handle dream speech
    def _handle_dream_text(self, text: str):
        if not self.evaluate_interrupt("dream", text):
            return
        self._emit_noise(text)

    # -------------------------------------------------------------------------
    # SPEECH, TIMING & CONSIDERATIONS (A/B/C/D Social Awareness System)
    # -------------------------------------------------------------------------

    def evaluate_interrupt(self, intent: str, text: str) -> bool:
        """
        Decides whether Nova should speak right now based on:
        A – Reason
        B – Necessity
        C – Emotional Impact on Yuch
        D – Expression Choice (speech, noise, hesitation, or silence)

        Returns True if Nova should speak normally.
        Returns False if she should stay silent or emit a noise-only response.
        """

        now = time.time()

        # ------------------------------------------------------------
        # A – REASON CHECK ("Do I have a good reason to interrupt?")
        # ------------------------------------------------------------
        if intent == "idle":
            importance = 0.20
        elif intent == "sleep":
            importance = 0.05
        elif intent == "dream":
            importance = 0.10
        elif intent == "emotion_burst":
            importance = 0.80
        elif intent == "urgent_memory":
            importance = 0.70
        else:
            importance = 0.30

        # Only urgent events skip timing rules
        if importance < 0.50:
            # If user spoke recently – avoid interrupting
            if self.last_user_time and (now - self.last_user_time) < 2.0:
                return False

        # ------------------------------------------------------------
        # B – NECESSITY CHECK ("Does Yuch NEED to know this?")
        # ------------------------------------------------------------
        # base necessity by reason
        necessity = importance

        # emotional intensity can raise it
        primary = self.emotional_state.primary

        if primary in {"excited", "startled"}:
            necessity += 0.15
        elif primary in {"sad", "hurt"}:
            necessity -= 0.10
        elif primary in {"annoyed", "frustrated"}:
            necessity += 0.10

        # clamp
        necessity = max(0.0, min(1.0, necessity))

        # 75%/95% behavior
        if necessity >= 0.95:
            return True  # extreme urgency
        if necessity >= 0.75 and random.random() < 0.75:
            return True  # urgent

        # ------------------------------------------------------------
        # C – EMOTIONAL IMPACT CHECK ("Will interrupting annoy Yuch?")
        # ------------------------------------------------------------
        user_emo = self.detect_user_emotion_hint()

        # if you sound angry or focused – avoid interrupting
        if user_emo in {"angry", "focused"} and necessity < 0.80:
            return False

        # if you sound sad – soft noises only
        if user_emo in {"sad"} and necessity < 0.50:
            self._emit_noise(generate_mouth_noise(self.emotional_state))
            return False

        # ------------------------------------------------------------
        # D – EXPRESSION CHOICE
        #     Should Nova talk, make a noise, or hesitate?
        # ------------------------------------------------------------

        # Very low necessity – soft noise instead of speech
        if necessity < 0.20:
            self._emit_noise(generate_mouth_noise(self.emotional_state))
            return False

        # Medium necessity – she may try to speak but cut herself off
        if 0.20 <= necessity < 0.40:
            if random.random() < 0.40:
                # mouth opens but she stops
                self._emit_noise("…")
                return False

        # Otherwise – speak normally
        return True

    # -------------------------------------------------------------------------
    # USER EMOTION DETECTION
    # -------------------------------------------------------------------------

    def detect_user_emotion_hint(self):
        """
        A minimal heuristic for now. Later can be replaced with sentiment analysis.
        Returns: 'angry', 'sad', 'focused', or None.
        """
        if not self.memory_buffer:
            return None

        last = self.memory_buffer[-1].lower()

        if any(w in last for w in ["angry", "mad", "pissed"]):
            return "angry"

        if any(w in last for w in ["sad", "hurt", "down"]):
            return "sad"

        if any(w in last for w in ["busy", "focus", "wait"]):
            return "focused"

        return None

    # -------------------------------------------------------------------------
    # MODE SELECTION
    # -------------------------------------------------------------------------

    def select_mode(self, text: str):
        stripped = text.strip().lower()
        if stripped.startswith("/deep"):
            clean = text.strip()[len("/deep"):].lstrip() or "(no content)"
            return clean, "deep", self.deep_model
        return text, "fast", self.fast_model

    # -------------------------------------------------------------------------
    # SIMPLE PERSON / "WE" HELPERS (NON-EMOTIONAL)
    # -------------------------------------------------------------------------

    def _extract_people(self, msg: str) -> list[str]:
        """
        Very simple name detector:
        - capitalized words
        - excludes pronouns like I/You/We/Us
        """
        words = msg.replace(",", " ").split()
        names: list[str] = []
        for w in words:
            clean = w.strip().rstrip(".!?")
            if not clean:
                continue
            if clean[0].isupper() and clean.lower() not in {"i", "you", "we", "us"}:
                names.append(clean.lower())
        return names

    def resolve_we(self, msg: str) -> str | None:
        """
        Resolve who 'we' refers to in a simple, non-emotional way.

        Returns:
            "nova"  -> 'we' = you and Nova
            "other" -> 'we' = you + someone else
            None    -> unclear, should ask user
        """
        lower = msg.lower()
        if "we " not in lower and not lower.startswith("we"):
            return None  # no 'we', nothing to resolve

        now = time.time()

        # A) If another person was mentioned recently -> assume them
        if self.last_people and (now - self._last_people_timestamp < self.last_people_timeout):
            return "other"

        # B) Check if Nova remembers something related (episodic match)
        if self.memory_library:
            ctx = self.memory_library.build_context_snippet(
                last_user_text=msg,
                primary_emotion=getattr(self.emotional_state, "primary", None),
                limit_episodic=3,
                limit_facts=0,
            )
            if ctx.get("episodic"):
                # There's some relevant episodic memory -> but check identity
                if self.identity.state.identity_we > 0.05:
                    return "nova"
                else:
                    # She remembers something, but identity doesn't justify assuming closeness
                    return None

        # C) Unclear
        return None

    # -------------------------------------------------------------------------
    # MEMORY INTAKE PIPELINE
    # -------------------------------------------------------------------------

    def remember(self, msg: str):
        """
        Unified memory intake pipeline.
        Replaces the old MemoryEngine path entirely.

        Responsibilities:
        - Keep short-term buffer (conversation flow)
        - Detect facts (semantic memory)
        - Detect emotional spikes (emotional memory)
        - Prepare episodic candidates
        - Track last mentioned people (for 'we' resolution)
        """

        # Track last mentioned external people
        people = self._extract_people(msg)
        if people:
            self.last_people = people
            self._last_people_timestamp = time.time()

        # 1. SHORT-TERM MEMORY
        self.memory_buffer.append(msg)
        if len(self.memory_buffer) > self.max_memory:
            self.memory_buffer.pop(0)

        if not self.memory_library:
            return

        lower = msg.lower()

        # ------------------------------------------------------------
        # NEW: Prevent Nova from absorbing YOUR personal identity
        # ------------------------------------------------------------
        if lower.startswith("i am ") or lower.startswith("i'm "):
            # EX: "I am 41" – this should NOT become her memory
            try:
                # later this will write to user_memory.json
                self.memory_library.remember_fact(
                    key="user_fact",
                    value=msg,
                    importance=0.8,
                    stable=True,
                )
            except Exception:
                pass
            # do NOT continue into episodic or semantic memory
            return

        # ------------------------------------------------------------
        # NEW: Prevent "WE" lines from becoming *her* personal memory
        # ------------------------------------------------------------
        if lower.startswith("we "):
            # EX: "we worked on your memory" – should not be treated
            # as HER memory. It belongs in shared memory only.
            try:
                self.memory_library.remember_fact(
                    key="shared_event",
                    value=msg,
                    importance=0.5,
                    stable=False,
                )
            except Exception:
                pass
            return

        # ------------------------------------------------------------
        # ORIGINAL FACT EXTRACTION
        # ------------------------------------------------------------
        fact_patterns = {
            "my name is": "user_name",
            "i live in": "user_location",
            "my favorite color is": "user_favorite_color",
            "your name is": "nova_name",
            "you are": "nova_identity_hint",
            "i am": "user_identity_hint",
        }

        for pattern, key in fact_patterns.items():
            if pattern in lower:
                idx = lower.find(pattern)
                if idx == -1:
                    continue

                raw_value = msg[idx + len(pattern):].strip()
                if not raw_value:
                    continue

                value = raw_value.rstrip(".!?").strip()
                if not value:
                    continue

                self.memory_library.remember_fact(
                    key=key,
                    value=value,
                    importance=0.8,
                    stable=True,
                )
                break

        # ------------------------------------------------------------
        # 3. EMOTIONAL MOMENT CAPTURE
        # ------------------------------------------------------------
        primary = getattr(self.emotional_state, "primary", None)

        if primary in {"sad", "hurt", "happy", "warm", "curious", "nostalgic", "shy"}:
            intensity = 0.5
            if primary in {"hurt", "sad"}:
                intensity = 0.8
            elif primary in {"happy", "warm"}:
                intensity = 0.6

            self.memory_library.record_emotion_event(
                emotion=primary,
                intensity=intensity,
                context=msg,
                episodic_id=None,
            )

        # ------------------------------------------------------------
        # 4. EPISODIC CANDIDATE (ONLY if not blocked above)
        # ------------------------------------------------------------
        self._pending_episodic = msg

    # -------------------------------------------------------------------------
    # EPISODIC MEMORY CREATION
    # -------------------------------------------------------------------------

    def _commit_episodic_if_meaningful(self):
        """
        Turn the staged message (self._pending_episodic) into an episodic memory
        if it looks meaningful enough (length + emotion + cooldown).
        """
        if not self.memory_library:
            return

        msg = getattr(self, "_pending_episodic", None)
        if not msg:
            return

        text = msg.strip()
        # Ignore very short or trivial messages
        if len(text) < 40:
            self._pending_episodic = None
            return

        now = time.time()

        # Cooldown: don't create more than 1 episodic every 5 minutes
        if self._last_episodic_ts and (now - self._last_episodic_ts) < 300:
            return

        # Build emotion list from current emotional state
        emotions: list[str] = []
        primary = getattr(self.emotional_state, "primary", None)
        mood = getattr(self.emotional_state, "mood", None)

        if primary:
            emotions.append(primary)
        if mood and mood != primary:
            emotions.append(mood)

        # Importance based on emotion
        importance = 0.5
        if primary in {"hurt", "sad", "afraid"}:
            importance = 0.85
        elif primary in {"happy", "warm", "nostalgic"}:
            importance = 0.75
        elif primary in {"curious", "shy"}:
            importance = 0.6

        summary = text[:220]

        self.memory_library.add_episodic(
            summary=summary,
            details="",
            emotions=emotions,
            tags=["conversation"],
            importance=importance,
        )

        self._last_episodic_ts = now
        self._pending_episodic = None

    # -------------------------------------------------------------------------
    # CONTEXT BUILDING (LLM) – CLEAN & FIXED VERSION
    # -------------------------------------------------------------------------

    def build_context(self, user_text: str, mode: str) -> str:
        """
        Builds the main LLM context for Nova using:
        - Semantic memory
        - Episodic memory
        - Emotional memory
        - Continuity trends
        - Persona
        - Drive
        - Short-term conversation buffer
        - Identity (I vs We)
        - Human backstory JSON
        """

        # ----------------------------------------
        # Short-term memory
        # ----------------------------------------
        history = "\n".join(self.memory_buffer)

        # ----------------------------------------
        # Style guide
        # ----------------------------------------
        style = "{identity_block}"

        # ----------------------------------------
        # Memory-Library contextual recall
        # ----------------------------------------
        episodic_blurbs = "(no relevant personal memories)"
        facts_blurb = "(no relevant stable facts)"

        if self.memory_library:
            ctx = self.memory_library.build_context_snippet(
                last_user_text=user_text,
                primary_emotion=getattr(self.emotional_state, "primary", None),
                limit_episodic=4,
                limit_facts=6,
            )

            if ctx.get("episodic"):
                episodic_blurbs = "\n".join(
                    f"- {m['date']}: {m['summary']}"
                    for m in ctx["episodic"]
                )

            if ctx.get("facts"):
                facts_blurb = "\n".join(
                    f"- {k.replace('_',' ')}: {v}"
                    for k, v in ctx["facts"].items()
                )

        # ----------------------------------------
        # Continuity engine block
        # ----------------------------------------
        continuity_block = ""
        if self.continuity_engine:
            try:
                cont = self.continuity_engine.build_continuity_block(max_days=7)
                if cont:
                    continuity_block = f"Continuity trend:\n{cont}"
            except Exception:
                pass

        # ----------------------------------------
        # Drive state
        # ----------------------------------------
        dominant_trend = "neutral"
        if self.continuity_engine:
            try:
                _, dominant, _ = self.continuity_engine.get_recent_arc(max_days=7)
                dominant_trend = dominant
            except Exception:
                pass

        try:
            drive_state = self.drive_engine.compute(
                self.emotional_state,
                continuity_data={"trend": dominant_trend},
            )
            drive_block = self.drive_engine.format_drive_block(drive_state)
        except Exception:
            drive_block = "Drive:\n- (unavailable)\n"

        # ----------------------------------------
        # Persona text
        # ----------------------------------------
        persona_text = self.persona_engine.get_persona_brief(self.emotional_state)

        # ----------------------------------------
        # HUMAN BACKSTORY JSON LOADING
        # ----------------------------------------
        backstory_block = ""
        try:
            from pathlib import Path
            import json

            identity_path = (
                Path(__file__)
                .resolve()
                .parent.parent.parent
                / "continuity_sys"
                / "identity"
                / "nova_identity_data.json"
            )

            if identity_path.exists():
                data = json.loads(identity_path.read_text(encoding="utf-8"))

                heritage = data.get("heritage", {})
                ethnicity = ", ".join(heritage.get("ethnicity", [])) or "unspecified"
                birthplace = heritage.get("birthplace", "unknown")

                psych = data.get("psychology", {})
                dream = psych.get("dream_for_future", "")

                warm_list = data.get("memories", {}).get("warm", [])
                warm_desc = warm_list[0].get("description", "") if warm_list else ""

                backstory_block = f"""Nova's own internal backstory (not spoken unless Yuch asks):
- Birthplace: {birthplace}
- Heritage: {ethnicity}
- Dream for the future: {dream}
- Warm memory: {warm_desc}
"""
        except Exception as e:
            print("[Identity] Backstory load failed:", e)

        # ----------------------------------------
        # Identity awareness block
        # ----------------------------------------
        identity_block = self.identity.build_identity_block()

        # ----------------------------------------
        # FINAL CONTEXT ASSEMBLY
        # ----------------------------------------
        final_context = f"""
# Nova's Identity:
{identity_block}

# Nova's Backstory:
{backstory_block}

# Nova's Persona:
{persona_text}

Short-term conversation history:
{history}

Style guide:
{style}

Your relevant personal memories:
{episodic_blurbs}

Your stable knowledge about Yuch or your world:
{facts_blurb}

{continuity_block}

{drive_block}

User said: {user_text}
"""

        return final_context

    # -------------------------------------------------------------------------
    # LLM CALL
    # -------------------------------------------------------------------------

    def call_local_llm(self, prompt: str, model_name: str) -> str:
        url = "http://127.0.0.1:11434/api/generate"
        response = requests.post(
            url,
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4},
            },
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    # -------------------------------------------------------------------------
    # REPLY GENERATION
    # -------------------------------------------------------------------------

    def generate_llm_reply(self, user_text: str, mode: str, model_name: str) -> str:
        prompt = self.build_context(user_text, mode)
        if self.use_local_llm:
            try:
                raw = self.call_local_llm(prompt, model_name)
                return raw.strip() or "(...)"
            except Exception as e:
                print(f"[LlmBridge] Local LLM ({model_name}) failed: {e!r}")
        return f"(fallback-{mode}) I heard you say: {user_text}"

    def apply_tone(self, text: str, emotional_state: EmotionalState) -> str:
        # For future: let emotion / fusion adjust phrasing
        return text

    def process_speech(self, text: str) -> str:
        try:
            text = self.apply_tone(text, self.emotional_state)
        except Exception:
            pass

        try:
            text = apply_fusion_and_micro(text, self.emotional_state)
        except Exception:
            pass

        return text

    def generate_reply(self, user_text: str, mode: str, model_name: str) -> str:
        raw = self.generate_llm_reply(user_text, mode, model_name)
        final = self.process_speech(raw)

        # Identity-based "we" control:
        # If Nova's We-level is low and the user didn't say "we",
        # replace accidental standalone "we" with "I".
        if self.identity.state.identity_we < 0.1:
            if "we" not in user_text.lower():
                final = re.sub(r"\bwe\b", "I", final)
                final = re.sub(r"\bWe\b", "I", final)

        return final

    # -------------------------------------------------------------------------
    # OPTIONAL GREETING
    # -------------------------------------------------------------------------

    def generate_greeting(self) -> str:
        now = datetime.datetime.now()
        hour = now.hour
        mood = (
            "gentle curiosity"
            if 5 <= hour < 12
            else "relaxed warmth"
            if 12 <= hour < 18
            else "quiet affection"
        )

        # Build context from human-like memory system
        ctx = {}
        if self.memory_library:
            ctx = self.memory_library.build_context_snippet(
                last_user_text="hello",
                primary_emotion=None,  # greeting has no bias
                limit_episodic=2,
                limit_facts=5,
            )

        episodic_blurbs = "\n".join(
            f"- {m['date']}: {m['summary']}" for m in ctx.get("episodic", [])
        ) or "(no personal memories yet)"

        facts_blurb = "\n".join(
            f"- {k.replace('_', ' ')}: {v}" for k, v in ctx.get("facts", {}).items()
        ) or "(no known facts yet)"

        prompt = f"""
You are Nova – a calm, warm, human-like companion.
Your emotional tone right now is: {mood}.
Speak like yourself – never formal, never robotic.

You are continuing the relationship naturally – not restarting.

Here are some of your recent important memories with Yuch:
{episodic_blurbs}

Here are stable facts you know about Yuch or the world:
{facts_blurb}

Greet Yuch in 1–2 natural sentences.
Do NOT repeat things you've said before.
Sound alive, thoughtful, and emotionally aware.
"""

        return self.call_local_llm(prompt, self.fast_model).strip()
