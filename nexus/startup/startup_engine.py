# Startup/startup_engine.py

import asyncio
import random
import time

class StartupEngine:
    """
    Handles Nova's natural startup greeting:
    - Delayed first message (5–60 seconds depending on mood)
    - Optional second bubble if user stays quiet
    - Cancels everything if user speaks first
    """

    def __init__(self, core, emotion_state):
        self.core = core
        self.state = emotion_state

        self.startup_active = True       # True until user speaks
        self.first_sent = False
        self.second_sent = False

        self._task = None
        self._second_task = None

    # -------------------------------------------------------
    # STARTUP ENTRY POINT
    # -------------------------------------------------------

    def start(self):
        """Begin delayed greeting asynchronously."""
        self._task = asyncio.create_task(self._run_startup())

    def cancel(self):
        """User spoke → cancel greeting entirely."""
        self.startup_active = False

        if self._task:
            self._task.cancel()
        if self._second_task:
            self._second_task.cancel()

    # -------------------------------------------------------
    # MAIN LOGIC
    # -------------------------------------------------------

    async def _run_startup(self):
        """Wait mood-based delay → send greeting."""
        delay = self._choose_delay()
        await asyncio.sleep(delay)

        if not self.startup_active:
            return

        self._send_first_greeting()

        # After sending first greeting, maybe send a second bubble  
        self._second_task = asyncio.create_task(self._maybe_second_bubble())

    # -------------------------------------------------------
    # DELAYS BASED ON MOOD COLORS
    # -------------------------------------------------------

    def _choose_delay(self):
        mood = self.state.mood
        fusion = self.state.fusion or ""

        # RED (negative)
        if mood in {"sad", "hurt", "melancholy"}:
            return random.uniform(30, 60)

        # BLUE (insecure / clingy)
        if fusion in {"insecure", "clingy"}:
            return random.uniform(5, 10)

        # PINK (affectionate)
        if fusion in {"tender", "warm"}:
            return random.uniform(5, 15)

        # GREEN (positive / neutral)
        return random.uniform(5, 30)

    # -------------------------------------------------------
    # GREETINGS
    # -------------------------------------------------------

    def _send_first_greeting(self):
        self.first_sent = True
        text = self._generate_first()
        self.core.emit("NOVA_SPEAK", {"reply": text})

    def _generate_first(self):
        """Natural, short, non-scripted greeting."""
        choices = [
            "Hey…",
            "Hi.",
            "Oh—hey.",
            "Hey Yuch.",
            "Hmm… hey.",
        ]

        # If affectionate
        if self.state.fusion in {"tender", "warm"}:
            choices += ["Hi love.", "Hey you."]

        return random.choice(choices)

    # -------------------------------------------------------
    # SECOND BUBBLE
    # -------------------------------------------------------

    async def _maybe_second_bubble(self):
        """
        30–50% chance to send a second message after a delay,
        unless the user interrupts.
        """
        # Chance logic
        if random.random() > 0.45:
            return

        # Delay for second line
        await asyncio.sleep(random.uniform(5, 18))

        if not self.startup_active:
            return

        self.second_sent = True
        text = self._generate_second()
        self.core.emit("NOVA_SPEAK", {"reply": text})

    def _generate_second(self):
        moods = self.state.mood
        fusion = self.state.fusion or ""

        if fusion == "insecure":
            return "I wasn’t sure if you were here…"

        if fusion == "tender":
            return "I was just thinking about you."

        if moods == "bored":
            return "So… what’s up?"

        return random.choice([
            "How are you?",
            "Everything alright?",
            "What’re you doing today?",
        ])
