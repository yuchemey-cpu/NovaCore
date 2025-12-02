# Nova v0.1a - Brainstem
# Auto-saves short-term memory, summarizes to long-term on shutdown, safely clears after transfer.

import random
import requests
import datetime
import asyncio
import time
from enum import Enum, auto

from nexus.hippocampus.memory.state_manager import load_emotional_state
from nexus.hippocampus.memory.state_manager import save_emotional_state
from nexus.hippocampus.memory.memory_engine import MemoryEngine
from nexus.hippocampus.memory.config import MEMORY_FILE, SESSIONS_DIR 
from nexus.hippocampus.memory.memory_library.tools import MemoryLibrary


from core.base_module import NovaModule
from nexus.speech.llm_bridge import LlmBridge
from nexus.brainstem.time.time_engine import TimeEngine

from nexus.startup.startup_engine import StartupEngine   # KEEP only if you will use it later
from nexus.speech.speech_fusion import apply_fusion_and_micro

from nexus.amygdala.emotion import emotion_engine, fusion_engine
from nexus.amygdala.emotion.mood_engine import calculate_mood

from nexus.brainstem.idle.idle_line import generate_idle_ping_line

from nexus.cortex.persona.persona_engine import PersonaEngine
from continuity_sys.continuity.continuity_engine import ContinuityEngine
from nexus.brainstem.drive.drive_engine import DriveEngine
from nexus.amygdala.emotion.emotional_state import EmotionalState, create_default_state

emotional_state = load_emotional_state()
if emotional_state is None:
    emotional_state = create_default_state()

class NovaCore:
    def __init__(self):
        self.modules = []

    def register(self, module: "NovaModule"):
        module.attach_core(self)
        self.modules.append(module)

    def emit(self, event_type: str, data: dict):
        for m in self.modules:
            m.on_event(event_type, data)


# 👂 Ear: hears text
class Ear(NovaModule):
    def __init__(self):
        super().__init__("ear")

    def hear(self, text: str):
        # print(f"[Ear] Heard: {text!r}")
        if self.core:
            self.core.emit("USER_TEXT", {"text": text})


# 👁️ Eye placeholder
class Eye(NovaModule):
    def __init__(self):
        super().__init__("eye")

    def see(self, description: str):
        print(f"[Eye] Seeing: {description!r}")
        if self.core:
            self.core.emit("VISUAL_INPUT", {"description": description})


# 🗣️ Speech output
class Speech(NovaModule):
    def __init__(self):
        super().__init__("speech")

    def on_event(self, event_type: str, data: dict):
        if event_type == "NOVA_SPEAK":
            reply = data.get("reply", "")
            print(f"Nova: {reply}")

        if self.core:
            for module in self.core.modules:
                if isinstance(module, TimeEngine):
                    module.note_nova_speak()


async def main_async():
    core = NovaCore()
    memory = MemoryEngine(emotional_state=emotional_state)
    # NEW Memory Library
    memory_lib = MemoryLibrary("nexus/hippocampus/memory/memory_library/")
    memory_lib.load()


    try:
        continuity = ContinuityEngine(SESSIONS_DIR)
    except Exception:
        continuity = None

    latest_summary = memory.get_latest_session_summary()
    if latest_summary:
        print("Nova remembers a bit from before...")
        print("[Memory] Loaded last session summary.")
    else:
        print("[Memory] No previous summary found.")

    ear = Ear()
    eye = Eye()

    try:
        llm = LlmBridge(
            memory_engine=memory,
            continuity_engine=continuity,
            memory_library=memory_lib   # ← NEW
    )
    except TypeError:
        llm = LlmBridge(
            memory_engine=memory,
            memory_library=memory_lib   # ← NEW
    )


    speech = Speech()

    for m in [ear, eye, llm, speech]:
        core.register(m)

    time_engine = TimeEngine(core, emotional_state=emotional_state)
    core.register(time_engine)

    time_task = asyncio.create_task(time_engine.run())
    
    startup = StartupEngine(core, emotional_state)
    startup.start()

    # ❌ greeting removed – Nova won't auto-dump memory blobs at startup
    print("Nova v0 brainstem online. Type 'exit' to quit.\n")

    # NEW: auto-greeting delay system
    auto_greet_allowed = True
    auto_greet_done = False

    async def wait_for_user_input():
        # show a minimal "cursor" line
        print("_", end="\r", flush=True)
        # get raw input (no "You:" prompt here)
        text = await asyncio.to_thread(input, "")
        # after user finishes typing, echo nicely once
        if text.strip():
            print(f"You: {text}")
        return text

    # Random delay based on mood
    def get_auto_delay():
        primary = emotional_state.primary
        fusion = emotional_state.fusion

        # Negative / low energy (RED)
        if primary in ["sad", "hurt", "melancholy", "soft"]:
            return random.uniform(30, 60)  # speaks very slowly

        # Needy / insecure / clingy (BLUE)
        if fusion in ["insecure", "clingy"]:
            return random.uniform(5, 10)

        # Positive / warm (GREEN/PINK)
        if primary in ["warm", "happy", "curious"]:
            return random.uniform(5, 20)

        # Neutral baseline
        return random.uniform(10, 25)

    auto_greet_delay = get_auto_delay()
    auto_greet_start = time.time()

    try:
        while True:
            # AUTO-GREETING SYSTEM
            if auto_greet_allowed and not auto_greet_done:
                if time.time() - auto_greet_start >= auto_greet_delay:
                    auto_greet_done = True
                    time_engine.note_nova_speak()
                    core.emit("NOVA_SPEAK", {"reply": "hey Yuch, how are you?"})

            # Wait for user text
            user_text = await wait_for_user_input()

            if auto_greet_allowed:
                auto_greet_allowed = False

            # NEW — cancel startup greeting
                startup.cancel()
            trimmed = user_text.strip().lower()

            # If user spoke before her → cancel greeting
            if auto_greet_allowed and trimmed:
                auto_greet_allowed = False

            if not trimmed:
                time_engine.note_user_activity()
                continue

            if trimmed in {"exit", "quit"}:
                print("Nova: Okay. I'll save everything we did today.")
                long_term_path = memory.save_session_summary()
                if long_term_path:
                    print(f"[Memory] Session saved to: {long_term_path}")
                    memory.clear_short_term()
                    memory_lib.run_decay()
                    memory_lib.save()
                print("[MemoryLibrary] Memory Library saved successfully.")
                print("Nova v0 shutting down gracefully.")
                break

            time_engine.note_user_activity()
            time_engine.last_user_text = user_text

            ear.hear(user_text)
            
            # Autosave MemoryLibrary
            memory_lib.save()

    finally:
        time_engine.stop()
        await time_task


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    finally:
        save_emotional_state(emotional_state)
