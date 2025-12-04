import asyncio

from nexus.cortex.thinking.brainloop import BrainLoop, BrainLoopConfig
from nexus.hippocampus.memory.state_manager import (
    load_emotional_state,
    save_emotional_state,
)


async def main_async() -> None:
    # Load emotional state from disk (or create a fresh one)
    emotional_state = load_emotional_state()

    # Build Nova's brain
    brain = BrainLoop(BrainLoopConfig(debug=False, allow_nsfw=False))

    # Inject loaded emotional state into the emotion engine
    try:
        brain.emotion_engine.state = emotional_state
    except Exception:
        pass

    print("Nova brain online. Type 'exit' to quit.\n")

    try:
        while True:
            user_text = await asyncio.to_thread(input, "You: ")
            user_text = user_text.strip()

            if not user_text:
                continue

            if user_text.lower() in {"exit", "quit"}:
                print("Nova: Okay. I'll remember today and rest for now.")
                break

            reply = brain.process_turn(user_text)
            print(f"Nova: {reply}")

        # End-of-session consolidation for episodic memory
        try:
            brain.memory_engine.consolidate_session()
        except Exception:
            pass

        # Persist advanced memory library
        try:
            brain.memory_library.save()
        except Exception:
            pass

    finally:
        # Save emotional state back to disk so Nova "remembers how she felt"
        try:
            save_emotional_state(brain.emotion_engine.state)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(main_async())
