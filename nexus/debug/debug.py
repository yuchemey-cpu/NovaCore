"""
NOVA DIAGNOSTIC PROTOCOL v2.0
Full Identity / Continuity / Memory / Emotion / Persona Diagnostic

Location:
    nexus/debug/debug.py

Run with:
    python -m nexus.debug.debug
from the project root (where the 'nova' package lives).
"""

import time
import traceback

# ==== IMPORT NOVACORE MODULES ====

from continuity_sys.identity.identity_engine import IdentityEngine
from continuity_sys.identity.relationship_state import RelationshipState
from continuity_sys.continuity.continuity_engine import ContinuityEngine

from nexus.cortex.persona.persona_engine import PersonaEngine

from nexus.hippocampus.memory.memory_engine import MemoryEngine
from nexus.hippocampus.memory.config import SESSIONS_DIR

from nexus.hippocampus.memory.state_manager import (
    load_emotional_state,
    save_emotional_state,
)

from nexus.amygdala.emotion import emotion_engine
from nexus.amygdala.emotion.emotional_state import EmotionalState


class NovaIdentityDiagnostic:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.start_time = time.time()

    # ------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------
    def log_error(self, message: str):
        self.errors.append(message)
        print(f"[ERROR] {message}")

    def log_warning(self, message: str):
        self.warnings.append(message)
        print(f"[WARN]  {message}")

    def log_ok(self, message: str):
        print(f"[OK]    {message}")

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------

    def test_identity_engine(self):
        """Check that IdentityEngine and identity JSON are healthy."""
        print("\n--- C1: Identity Engine / Identity JSON ---")
        try:
            engine = IdentityEngine()
        except Exception as e:
            self.log_error(
                f"IdentityEngine failed to initialize:\n{traceback.format_exc()}"
            )
            return

        # Basic name check
        name = engine.identity_data.get("name")
        if not name:
            self.log_error("Identity JSON missing 'name' field.")
        else:
            self.log_ok(f"Identity name loaded: {name!r}")

        # Expect some structured fields to exist
        required_keys = ["Age", "heritage", "life_timeline", "psychology"]
        for key in required_keys:
            if key not in engine.identity_data:
                self.log_warning(f"Identity JSON missing optional key: {key}")
        self.log_ok("Identity JSON loaded and parsed.")

        # Relationship stage sanity
        stage = engine.state.stage
        if not isinstance(stage, str) or not stage:
            self.log_error("IdentityEngine.state.stage is missing or invalid.")
        else:
            self.log_ok(f"Relationship stage is: {stage}")

    def test_relationship_state(self):
        """Ensure RelationshipState defaults are sane."""
        print("\n--- C2: RelationshipState ---")
        try:
            rel = RelationshipState()
        except Exception:
            self.log_error("RelationshipState failed to construct.")
            return

        # Basic range sanity checks
        sliders = [
            ("identity_i", rel.identity_i),
            ("identity_we", rel.identity_we),
            ("independence", rel.independence),
            ("dependence", rel.dependence),
        ]

        for name, value in sliders:
            if not (0.0 <= value <= 1.0):
                self.log_error(f"RelationshipState.{name}={value} out of [0,1] range.")
        if not self.errors:
            self.log_ok("RelationshipState sliders are within valid ranges.")

    def test_continuity_engine(self):
        """Check that ContinuityEngine can read sessions and build continuity block."""
        print("\n--- C3: ContinuityEngine ---")
        try:
            continuity = ContinuityEngine(sessions_dir=SESSIONS_DIR)
        except Exception:
            self.log_error(
                "ContinuityEngine failed to initialize "
                f"(sessions_dir={SESSIONS_DIR!r})."
            )
            return

        try:
            block = continuity.build_continuity_block(max_days=7)
            if not isinstance(block, str):
                self.log_error(
                    "ContinuityEngine.build_continuity_block() did not return a string."
                )
            else:
                preview = block.replace("\n", " ")[:120]
                self.log_ok(f"Continuity block generated (preview): {preview!r}")
        except Exception:
            self.log_error(
                "ContinuityEngine.build_continuity_block() raised an exception:\n"
                + traceback.format_exc()
            )

    def test_memory_engine(self):
        """Exercise MemoryEngine basic load and add_memory behavior."""
        print("\n--- C4: MemoryEngine ---")
        try:
            # Use a neutral emotional state for the diary-style engine
            heart = EmotionalState(baseline="curious")
            mem = MemoryEngine(emotional_state=heart)
        except Exception:
            self.log_error(
                "MemoryEngine failed to initialize:\n" + traceback.format_exc()
            )
            return

        try:
            before_count = len(mem.memories)
            mem.add_memory(
                "[diagnostic] NovaCore identity diagnostic test entry.", importance=0.1
            )
            after_count = len(mem.memories)

            if after_count <= before_count:
                self.log_warning(
                    "MemoryEngine.add_memory() did not increase the in-memory count. "
                    "This may be okay if compression merged topics."
                )
            else:
                self.log_ok(
                    f"MemoryEngine.add_memory() added an entry "
                    f"({before_count} -> {after_count})."
                )
        except Exception:
            self.log_error(
                "MemoryEngine.add_memory() raised an exception:\n"
                + traceback.format_exc()
            )

    def test_emotion_system(self):
        """Check emotional_state load/save and update_emotional_state pipeline."""
        print("\n--- C5: Emotion System ---")
        try:
            state = load_emotional_state()
        except Exception:
            self.log_error(
                "load_emotional_state() failed:\n" + traceback.format_exc()
            )
            return

        if not isinstance(state, EmotionalState):
            self.log_error(
                "load_emotional_state() did not return an EmotionalState instance."
            )
            return

        self.log_ok(
            f"Loaded EmotionalState: baseline={state.baseline}, "
            f"mood={state.mood}, primary={state.primary}"
        )

        # Try an update
        try:
            updated = emotion_engine.update_emotional_state(
                state, heard_text="This is a small diagnostic check."
            )
            if not isinstance(updated, EmotionalState):
                self.log_error(
                    "emotion_engine.update_emotional_state() "
                    "did not return an EmotionalState."
                )
            else:
                self.log_ok(
                    f"Emotion updated: primary={updated.primary}, "
                    f"mood={updated.mood}, baseline={updated.baseline}"
                )
        except Exception:
            self.log_error(
                "emotion_engine.update_emotional_state() raised an exception:\n"
                + traceback.format_exc()
            )
            return

        # Test saving
        try:
            save_emotional_state(state)
            self.log_ok("save_emotional_state() completed without error.")
        except Exception:
            self.log_error(
                "save_emotional_state() raised an exception:\n"
                + traceback.format_exc()
            )

    def test_persona_engine(self):
        """Check PersonaEngine can build a persona brief with and without emotion."""
        print("\n--- C6: PersonaEngine ---")
        try:
            persona = PersonaEngine()
        except Exception:
            self.log_error(
                "PersonaEngine failed to initialize:\n" + traceback.format_exc()
            )
            return

        try:
            brief_core = persona.get_persona_brief(emotional_state=None)
            if not isinstance(brief_core, str) or not brief_core.strip():
                self.log_error(
                    "PersonaEngine.get_persona_brief(None) returned empty / non-string."
                )
            else:
                preview = brief_core.replace("\n", " ")[:120]
                self.log_ok(f"Core persona brief generated (preview): {preview!r}")
        except Exception:
            self.log_error(
                "PersonaEngine.get_persona_brief(None) raised an exception:\n"
                + traceback.format_exc()
            )

        # With emotional influence
        try:
            state = load_emotional_state()
            brief_with_emotion = persona.get_persona_brief(emotional_state=state)
            if not isinstance(brief_with_emotion, str) or not brief_with_emotion.strip():
                self.log_error(
                    "PersonaEngine.get_persona_brief(emotional_state) "
                    "returned empty / non-string."
                )
            else:
                preview = brief_with_emotion.replace("\n", " ")[:120]
                self.log_ok(
                    "Persona persona+emotion brief generated (preview): "
                    f"{preview!r}"
                )
        except Exception:
            self.log_error(
                "PersonaEngine.get_persona_brief(emotional_state) raised "
                "an exception:\n" + traceback.format_exc()
            )

    # ------------------------------------------------------------
    # Report
    # ------------------------------------------------------------
    def report(self):
        print("\n========== NOVA DIAGNOSTIC REPORT ==========")
        elapsed = time.time() - self.start_time
        print(f"Run time: {elapsed:.3f}s")
        print(f"Errors:   {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n❌ FAIL — one or more subsystems have issues.\n")
        else:
            print("\n✔ PASS — all checked subsystems are healthy.\n")

        print("============================================\n")


def main():
    diag = NovaIdentityDiagnostic()
    diag.test_identity_engine()
    diag.test_relationship_state()
    diag.test_continuity_engine()
    diag.test_memory_engine()
    diag.test_emotion_system()
    diag.test_persona_engine()
    diag.report()


if __name__ == "__main__":
    main()
