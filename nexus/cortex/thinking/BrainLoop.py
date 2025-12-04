# brainloop.py
# NovaCore - BrainLoop
# Orchestrates Nova's internal cycle each time the user sends a message.
# This pulls together all brain modules, updates state, builds intent,
# and sends it to the LLM through LlmBridge.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

# Emotion / affection
from nexus.amygdala.emotion.emotion_engine import EmotionEngine
from nexus.amygdala.affection.affection_engine import AffectionEngine

# Brainstem: needs, drives, daily cycle, idle life
from nexus.brainstem.needs.needs_engine import NeedsEngine
from nexus.brainstem.drive.drive_engine import DriveEngine
from nexus.brainstem.daily_cycle.daily_cycle_engine import DailyCycleEngine
from nexus.brainstem.idle.idle_engine import IdleLifeEngine

# Persona / maturity / thinking
from nexus.cortex.persona.maturity_engine import MaturityInputs, MaturityEngine
from nexus.cortex.persona.persona_engine import PersonaEngine
from nexus.cortex.thinking.intent_builder import (
    IntentBuilder,
    IntentContext,
    MemorySnippet,
    EmotionSnapshot,
    MoodSnapshot,
    NeedsSnapshot,
    RelationshipSnapshot,
)
from nexus.cortex.thinking.inner_voice import InnerVoice
from nexus.cortex.thinking.initiative_engine import InitiativeEngine

# Identity + continuity
from continuity_sys.identity.identity_engine import IdentityEngine
from continuity_sys.continuity.continuity_engine import ContinuityEngine

# Memory systems
from nexus.hippocampus.memory.memory_engine import MemoryEngine
from nexus.hippocampus.memory.memory_library.tools import MemoryLibrary
from nexus.hippocampus.memory.config import LONG_TERM_DIR, SESSIONS_DIR
from nexus.hippocampus.memory.memory_consolidation import MemoryConsolidationEngine
from nexus.hippocampus.state.nova_state import NovaState

# Speech
from nexus.speech.llm_bridge import LlmBridge
from nexus.speech.speech_post_processor import SpeechPostProcessor


@dataclass
class BrainLoopConfig:
    allow_nsfw: bool = False
    debug: bool = False


class BrainLoop:
    """
    Main orchestrator for Nova's turn-by-turn cognition.

    High-level steps:
        1. Receive user message
        2. Update emotional state / needs / drives / relationship
        3. Update memory + continuity
        4. Compute maturity
        5. Update NovaState
        6. Build IntentContext
        7. IntentBuilder -> Intent (+ initiative + inner voice)
        8. LlmBridge -> reply text
        9. Post-process speech + log reply to memory
    """

    def __init__(self, config: Optional[BrainLoopConfig] = None):
        self.config = config or BrainLoopConfig()

        # Emotion / affection
        self.emotion_engine = EmotionEngine()
        self.affection_engine = AffectionEngine()

        # Persona / maturity
        self.maturity_engine = MaturityEngine()
        self.persona_engine = PersonaEngine()

        # Identity / continuity
        self.identity_engine = IdentityEngine()
        self.continuity_engine = ContinuityEngine(SESSIONS_DIR)

        # Memory systems
        self.memory_engine = MemoryEngine(base_dir=LONG_TERM_DIR)
        self.memory_library = MemoryLibrary("nexus/hippocampus/memory/memory_library/")
        try:
            self.memory_library.load()
        except Exception:
            # Start empty if load fails
            pass
        self.memory_consolidation = MemoryConsolidationEngine()

        # Brainstem cycles
        self.idle_engine = IdleLifeEngine()
        self.idle_engine.register_user_activity()

        self.drive_engine = DriveEngine()
        self.needs_engine = NeedsEngine()
        self.daily_cycle = DailyCycleEngine()

        # Thinking / speech
        self.intent_builder = IntentBuilder()
        self.llm_bridge = LlmBridge()
        self.speech_post = SpeechPostProcessor()

        # Shared long-lived state
        self.nova_state = NovaState()

        # Higher-level cognition helpers
        self.inner_voice = InnerVoice()
        self.initiative_engine = InitiativeEngine()

    # ------------------------------------------------------------
    # Main Entry
    # ------------------------------------------------------------

    def process_turn(self, user_message: str) -> str:
        """
        Called every time the user speaks.
        Returns Nova's generated reply.
        """

        # Idle-life: mark recent activity
        self.idle_engine.register_user_activity()

        # 1) Emotion update
        emotional_input = self.emotion_engine.detect_user_emotion(user_message)
        emotional_state = self.emotion_engine.update(emotional_input)

        # Estimate intensity / stability for newer modules
        emotional_state.intensity = self._estimate_intensity(emotional_state)
        emotional_state.stability = 0.7

        # 2) Drives & needs
        needs_state = self.needs_engine.update()
        drive_state = self.drive_engine.compute(emotional_state)

        # 3) Sleep / daily cycle (very lightweight)
        if getattr(self.daily_cycle.state, "is_asleep", False):
            wake_msg = self.daily_cycle.update_sleep(self.nova_state)
            if wake_msg:
                return wake_msg
        else:
            try:
                should_sleep = self.daily_cycle.check_sleep_need(
                    needs_state, emotional_state, drive_state
                )
            except Exception:
                should_sleep = False
            if should_sleep:
                sleep_msg = self.daily_cycle.sleep(self.nova_state)
                return sleep_msg

        # 4) Relationship state
        relationship_state = self.identity_engine.update_relationship(user_message)

        # 5) Memory update (short-term buffer)
        try:
            self.memory_engine.on_user_message(
                user_message, emotion=getattr(emotional_state, "primary", None)
            )
        except Exception:
            pass

        recent_memory_snips: List[MemorySnippet] = []
        try:
            for ev in self.memory_engine.short_term[-5:]:
                recent_memory_snips.append(
                    MemorySnippet(
                        text=ev.text,
                        weight=0.6 if getattr(ev, "speaker", "user") == "user" else 0.4,
                        kind="recent",
                    )
                )
        except Exception:
            recent_memory_snips = []

        # 6) Continuity update
        try:
            self.continuity_engine.on_user_message(user_message)
        except Exception:
            pass

        # 7) Persona / maturity
        persona_brief = self.persona_engine.get_persona_brief()

        # Mood snapshot from emotional_state.mood
        mood_snapshot = MoodSnapshot(
            label=getattr(emotional_state, "mood", "neutral"),
            valence=self._estimate_mood_valence(getattr(emotional_state, "mood", "")),
            energy=0.5,
        )

        maturity_inputs = self._build_maturity_inputs(
            emotional_state=emotional_state,
            mood_state=mood_snapshot,
            relationship_state=relationship_state,
            drive_state=drive_state,
            needs_state=needs_state,
        )
        maturity_score = self.maturity_engine.compute(maturity_inputs)

        # 8) Build emotion / needs / relationship snapshots
        emotion_snap = EmotionSnapshot(
            primary=emotional_state.primary,
            fusion=getattr(emotional_state, "fusion", None),
            intensity=getattr(emotional_state, "intensity", 0.5),
            stability=getattr(emotional_state, "stability", 0.5),
        )

        needs_snap = NeedsSnapshot(
            hunger=needs_state.hunger,
            thirst=needs_state.thirst,
            fatigue=needs_state.fatigue,
            bladder=needs_state.bladder,
        )

        relationship_snap = RelationshipSnapshot(
            label=getattr(relationship_state, "label", "stranger"),
            level=getattr(relationship_state, "level", 0),
            trust=getattr(relationship_state, "trust", 0.2),
            safety=getattr(relationship_state, "safety", 0.2),
            attachment=getattr(relationship_state, "attachment", 0.0),
        )

        # 9) Continuity snippets (CCE / DDE / TEE)
        continuity_snips: List[MemorySnippet] = []
        try:
            parts: List[str] = []

            if hasattr(self.continuity_engine, "build_cce_context"):
                cce = self.continuity_engine.build_cce_context()
                if cce and cce.strip():
                    parts.append(cce.strip())

            if hasattr(self.continuity_engine, "build_dde_context"):
                dde = self.continuity_engine.build_dde_context()
                if dde and dde.strip():
                    parts.append(dde.strip())

            if hasattr(self.continuity_engine, "check_timed_expectations"):
                self.continuity_engine.check_timed_expectations()
            if hasattr(self.continuity_engine, "build_tee_context"):
                tee = self.continuity_engine.build_tee_context()
                if tee and tee.strip():
                    parts.append(tee.strip())

            if parts:
                continuity_snips.append(
                    MemorySnippet(
                        text=" ".join(parts),
                        weight=0.85,
                        kind="continuity",
                    )
                )
        except Exception:
            continuity_snips = []

        # 10) Episodic memory recall (from MemoryEngine)
        episodic_from_engine: List[MemorySnippet] = []
        try:
            episodic_list = self.memory_engine.get_relevant_episodic(
                user_message, limit=3
            )
            for ep in episodic_list:
                episodic_from_engine.append(
                    MemorySnippet(
                        text=str(ep).strip(),
                        weight=0.55,
                        kind="episodic",
                    )
                )
        except Exception:
            episodic_from_engine = []

        episodic_all = continuity_snips + episodic_from_engine

        # 11) Update NovaState for this turn
        self.nova_state.update_turn(
            user_message=user_message,
            new_emotion=emotion_snap,
            new_mood=mood_snapshot,
            new_needs=needs_snap,
            new_relationship=relationship_snap,
            maturity=maturity_score,
            persona_brief=persona_brief,
            recent_memory=recent_memory_snips,
            episodic_memory=episodic_all,
            new_drive=drive_state,
        )

        # 12) Affection engine update
        affection_state = self.affection_engine.update(self.nova_state)

        # 13) Build IntentContext
        q_type = self._classify_question(user_message)

        ctx = IntentContext(
            user_message=user_message,
            emotion=self.nova_state.emotion,
            mood=self.nova_state.mood,
            needs=self.nova_state.needs,
            relationship=self.nova_state.relationship,
            maturity=self.nova_state.maturity,
            persona_brief=self.nova_state.persona_brief,
            recent_memory=self.nova_state.recent_memory,
            episodic_memory=self.nova_state.episodic_memory,
            allow_nsfw=self.config.allow_nsfw,
            affection=affection_state.affection,
            arousal=affection_state.arousal,
            comfort=affection_state.comfort,
            fluster=affection_state.fluster,
            nsfw_readiness=affection_state.readiness,
            question_type=q_type,
            is_direct_question=q_type != "generic",
        )

        # 14) IntentBuilder -> Intent
        intent = self.intent_builder.build_intent(ctx)

        # 15) Initiative
        initiative_intent = self.initiative_engine.evaluate(self.nova_state, ctx)

        if ctx.is_direct_question:
            initiative_intent = None

        if initiative_intent:
            if initiative_intent.priority > 0.6:
                intent.content_goal = initiative_intent.content
                intent.speaking_mode = "question"
            else:
                intent.ask_back = False
                intent.memory_hint = initiative_intent.content

        # 16) Inner Voice -> modifies intent silently
        thoughts = self.inner_voice.generate(ctx, self.nova_state)
        intent = self.inner_voice.merge_into_intent(intent, thoughts)

        # 17) LLM Bridge
        reply = self.llm_bridge.generate_reply(
            user_message=user_message,
            intent=intent,
            persona_brief=persona_brief,
        )

        # 18) Speech micro-layer (post-processing)
        reply = self.speech_post.process(reply, intent)

        # 19) Memory the reply
        try:
            self.memory_engine.on_nova_message(reply)
        except Exception:
            pass

        # 20) Save reply to NovaState
        self.nova_state.record_reply(reply)

        # 21) (Optional) event logging hook
        self._persist_significant_events(self.nova_state)

        # 22) Consolidate memory (higher-level)
        self.memory_consolidation.consolidate(self.nova_state)

        return reply

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _classify_question(self, text: str) -> str:
        text_low = text.lower().strip()
        if "how are you" in text_low:
            return "how_are_you"
        if text_low.startswith("what if"):
            return "what_if"
        if "do you like" in text_low:
            return "preference"
        return "generic"

    def _build_maturity_inputs(
        self,
        emotional_state,
        mood_state: MoodSnapshot,
        relationship_state,
        drive_state,
        needs_state,
    ) -> MaturityInputs:
        base_maturity = 0.5
        if hasattr(self.identity_engine, "base_maturity"):
            try:
                base_maturity = self.identity_engine.base_maturity()
            except Exception:
                base_maturity = 0.5

        return MaturityInputs(
            identity_base=base_maturity,
            relationship_level=getattr(relationship_state, "level", 0),
            mood_balance=mood_state.valence,
            emotional_intensity=getattr(emotional_state, "intensity", 0.5),
            emotional_stability=getattr(emotional_state, "stability", 0.5),
            need_pressure=needs_state.pressure,
        )

    def _estimate_intensity(self, state) -> float:
        """
        Rough intensity heuristic based on whether emotion is neutral
        and how often it has appeared recently.
        """
        primary = getattr(state, "primary", "neutral") or "neutral"
        history = getattr(state, "history", []) or []

        if not history:
            return 0.3

        recent = history[-5:]
        count = sum(1 for e in recent if e == primary)

        base = 0.3
        if primary not in ("neutral", "bored"):
            base += 0.1

        return max(0.0, min(1.0, base + 0.1 * count))

    def _estimate_mood_valence(self, mood_label: str) -> float:
        """
        Map mood labels to a simple valence estimate (0.0–1.0).
        """
        mood = (mood_label or "").lower()
        positive = {"happy", "excited", "curious", "warm", "calm"}
        negative = {"sad", "afraid", "bored", "angry", "hurt", "lonely"}

        if mood in positive:
            return 0.7
        if mood in negative:
            return 0.3
        return 0.5

    def _persist_significant_events(self, nova_state: NovaState) -> None:
        """
        Placeholder for long-term event logging.

        The original design used a separate StateManager to persist
        emotional spikes, relationship changes, and vulnerability events.
        That manager is not present in this codebase yet, so this method
        intentionally does nothing while keeping the hook in place.
        """
        return

