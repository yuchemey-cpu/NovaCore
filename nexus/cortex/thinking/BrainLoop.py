# brainloop.py
# NovaCore - BrainLoop
# Orchestrates Nova's internal cycle each time the user sends a message.
# This pulls together all brain modules, updates state, builds intent,
# and sends it to the LLM through LlmBridge.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any

# Import brain modules (you will adjust paths as needed)
from nexus.amygdala.emotion.emotion_engine import EmotionEngine
from nexus.amygdala.emotion.fusion_engine import FusionEngine
from nexus.amygdala.emotion.mood_engine import MoodEngine
from nexus.amygdala.affection.affection_engine import AffectionEngine


from nexus.brainstem.needs.needs_engine import NeedsEngine
from brainstem.drive.drive_engine import DriveEngine
from nexus.brainstem.daily_cycle.daily_cycle_engine import DailyCycleEngine



from nexus.cortex.persona.maturity_engine import MaturityInputs
from nexus.cortex.persona.maturity_engine import MaturityEngine
from nexus.cortex.persona.persona_engine import PersonaEngine
from nexus.cortex.thinking.intent_builder import IntentBuilder, IntentContext
from nexus.cortex.thinking.inner_voice import InnerVoice
from nexus.cortex.thinking.initiative_engine import InitiativeEngine



from continuity_sys.identity.identity_engine import IdentityEngine
from continuity_sys.continuity.continuity_engine import ContinuityEngine

from nexus.hippocampus.memory.memory_engine import MemoryEngine
from nexus.hippocampus.memory.memory_library import MemoryLibrary
from nexus.hippocampus.memory.state_manager import StateManager
from nexus.hippocampus.state.nova_state import NovaState
from nexus.hippocampus.memory.memory_consolidation import MemoryConsolidationEngine

from brainstem.drive.drive_engine import DriveEngine
# (Optionally future: needs engine)

from nexus.speech.llm_bridge import LlmBridge
from nexus.speech.speech_post_processor import SpeechPostProcessor


@dataclass
class BrainLoopConfig:
    allow_nsfw: bool = False
    debug: bool = False


class BrainLoop:
    """
    Main orchestrator for Nova's turn-by-turn cognition.

    Steps:
        1. Receive user message
        2. Update emotional state
        3. Update drives / needs
        4. Update mood
        5. Update relationship context
        6. Update memories
        7. Compute maturity
        8. Build IntentContext
        9. IntentBuilder -> Intent
        10. LlmBridge -> final spoken text
        11. Apply speech_micro (outside this file)
    """

    def __init__(self, config: Optional[BrainLoopConfig] = None):
        self.config = config or BrainLoopConfig()

        # --- Engine instances ---
        self.emotion_engine = EmotionEngine()
        self.fusion_engine = FusionEngine()
        self.mood_engine = MoodEngine()
        self.affection_engine = AffectionEngine()


        self.maturity_engine = MaturityEngine()
        self.persona_engine = PersonaEngine()

        self.identity_engine = IdentityEngine()
        self.continuity_engine = ContinuityEngine()

        self.memory_engine = MemoryEngine()
        self.memory_library = MemoryLibrary()
        self.memory_consolidation = MemoryConsolidationEngine()


        self.drive_engine = DriveEngine()
        self.needs_engine = NeedsEngine()
        self.daily_cycle = DailyCycleEngine()


        self.intent_builder = IntentBuilder()
        self.llm_bridge = LlmBridge()
        
        self.state_manager = StateManager()
        self.nova_state = NovaState()
        
        self.speech_post = SpeechPostProcessor()
        
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
        # 1) Update emotional input from message
        emotional_input = self.emotion_engine.detect_user_emotion(user_message)
        emotional_state = self.emotion_engine.update(emotional_input)

        # 2) Drives (hunger, fatigue, etc.)
        drive_state = self.drive_engine.update()
        needs_state = self.needs_engine.update()
        
        # Sleep / daily cycle check
        if self.daily_cycle.state.is_asleep:
            wake_msg = self.daily_cycle.update_sleep(self.nova_state)
            if wake_msg:
                # Nova wakes up
                return wake_msg

        else:
            should_sleep = self.daily_cycle.check_sleep_need(needs_state, emotional_state, drive_state)
            if should_sleep:
                sleep_msg = self.daily_cycle.sleep(self.nova_state)
                return sleep_msg

        # 3) Mood update
        mood_state = self.mood_engine.update(emotional_state)

        # 4) Relationship state (identity engine tracks who user is to Nova)
        relationship_state = self.identity_engine.update_relationship(user_message)

        # 5) Short-term memory update
        self.memory_engine.store_turn(user_message, emotional_state)
        recent_memory_snips = self.memory_engine.recent_snippets()
        episodic_snips = self.memory_library.relevant_memories(emotional_state)

        # 6) Continuity (longer arcs)
        self.continuity_engine.update(user_message, emotional_state)

        # 7) Persona / maturity
        persona_brief = self.persona_engine.get_persona_brief()
        maturity_inputs = self._build_maturity_inputs(
            emotional_state=emotional_state,
            mood_state=mood_state,
            relationship_state=relationship_state,
            drive_state=drive_state,
            needs_state=needs_state,
        )
        maturity_score = self.maturity_engine.compute(maturity_inputs)

        # 8) Fusion (sad+lonely= insecure, etc.)
        fusion_label = self.fusion_engine.compute(emotional_state)
        emotional_state.fusion = fusion_label

        # 9) Update NovaState for this turn
        self.nova_state.update_turn(
            user_message=user_message,
            new_emotion=emotional_state,
            new_mood=mood_state,
            new_drive=drive_state,
            new_needs=needs_state,
            new_relationship=relationship_state,
            maturity=maturity_score,
            persona_brief=persona_brief,
            recent_memory=recent_memory_snips,
            episodic_memory=episodic_snips,
        )

        # 9.5) Affection engine update
        affection_state = self.affection_engine.update(self.nova_state)
        
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

            affection=self.affection_engine.state.affection,
            arousal=self.affection_engine.state.arousal,
            nsfw_readiness=self.affection_engine.state.readiness,
            fluster=self.affection_engine.state.fluster,
            comfort=self.affection_engine.state.comfort,

            question_type=self._classify_question(user_message),
            is_direct_question=self._classify_question(user_message) != "generic",
        )          

        # 10) IntentBuilder -> Intent
        intent = self.intent_builder.build_intent(ctx)
        
        # 10.5) Initiative
        initiative_intent = self.initiative_engine.evaluate(self.nova_state, ctx)

        # no initiative on direct questions
        if ctx.is_direct_question:
            initiative_intent = None

        if initiative_intent:
            if initiative_intent.priority > 0.6:
                intent.content_goal = initiative_intent.content
                intent.speaking_mode = "question"
            else:
                intent.ask_back = False
                intent.memory_hint = initiative_intent.content

        # 10.6) Inner Voice -> modifies intent silently
        thoughts = self.inner_voice.generate(ctx, self.nova_state)
        intent = self.inner_voice.merge_into_intent(intent, thoughts)

        # 11) LLM Bridge
        reply = self.llm_bridge.generate_reply(
            user_message=user_message,
            intent=intent,
            persona_brief=persona_brief,
        )

        # 11.5) Speech micro-layer (post-processing)
        reply = self.speech_post.process(reply, intent)

        # 12) Memory the reply
        self.memory_engine.store_turn(reply, emotional_state=None, speaker="nova")

        # Save reply to NovaState
        self.nova_state.record_reply(reply)

        # 13) Persist significant moments to state_manager
        self._persist_significant_events(self.nova_state)
        
        #14) Consolidate memory
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

    def _build_maturity_inputs(self, emotional_state, mood_state, relationship_state, drive_state, needs_state):
        return MaturityInputs(
            identity_base=self.identity_engine.base_maturity(),
            relationship_level=relationship_state.level,
            mood_balance=mood_state.valence,
            emotional_intensity=emotional_state.intensity,
            emotional_stability=emotional_state.stability,
            need_pressure=needs_state.pressure,
        )
        
    def _persist_significant_events(self, nova_state: NovaState):
        """
        Stores meaningful emotional / relational events into long-term memory.
        We DO NOT store every turn, only spikes or important changes.
        """

        # Emotional spike detection
        if nova_state.emotion.intensity > 0.65:
            self.state_manager.save_event(
                "emotional_spike",
                {
                    "emotion": nova_state.emotion.primary,
                    "fusion": nova_state.emotion.fusion,
                    "intensity": nova_state.emotion.intensity,
                    "turn": nova_state.turn_count,
                    "context": nova_state.last_user_message,
                }
            )

        # Relationship change
        if nova_state.relationship.attachment > 0.6:
            self.state_manager.save_event(
                "relationship_update",
                {
                    "relationship": nova_state.relationship.label,
                    "attachment": nova_state.relationship.attachment,
                    "trust": nova_state.relationship.trust,
                    "turn": nova_state.turn_count,
                }
            )

        # If Nova expresses vulnerability
        if nova_state.maturity < 0.45 and nova_state.emotion.intensity > 0.4:
            self.state_manager.save_event(
                "vulnerability_event",
                {
                    "emotion": nova_state.emotion.primary,
                    "fusion": nova_state.emotion.fusion,
                    "relationship": nova_state.relationship.label,
                    "turn": nova_state.turn_count,
                }
            )
