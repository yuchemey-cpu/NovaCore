import time
import asyncio
import random
from enum import Enum, auto

from core.base_module import NovaModule
from nexus.brainstem.idle.idle_line import generate_idle_ping_line
from nexus.amygdala.emotion import fusion_engine
from nexus.speech.speech_fusion import apply_fusion_tone


class IdleState(Enum):
    AWAKE = auto()
    RESTING = auto()
    SLEEPY = auto()
    ASLEEP = auto()


class TimeEngine(NovaModule):
    def __init__(
        self,
        core,
        emotional_state,
        ping_after=180.0,
        rest_after=600.0,
        sleep_after=1800.0,
        check_interval=5.0,
    ):
        super().__init__("time_engine")
        self.core = core
        self.emotional_state = emotional_state

        self.ping_after = ping_after
        self.rest_after = rest_after
        self.sleep_after = sleep_after
        self.check_interval = check_interval

        now = time.time()
        self.last_user_time = now
        self.last_nova_time = now
        self.last_user_text = None

        self._wake_requested = False
        self.state = IdleState.AWAKE
        self._running = True

        self._did_ping = False
        self._did_lie_down = False
        self._did_sleep = False

    # ---------------------------------------------------------
    # External triggers
    # ---------------------------------------------------------

    def note_user_activity(self):
        self.last_user_time = time.time()
        self.state = IdleState.AWAKE
        self._wake_requested = True
        self._did_ping = False
        self._did_lie_down = False
        self._did_sleep = False

    def note_nova_speak(self):
        self.last_nova_time = time.time()

    # ---------------------------------------------------------
    # Async loop
    # ---------------------------------------------------------

    async def run(self):
        while self._running:
            await asyncio.sleep(self.check_interval)
            self._tick()

    def stop(self):
        self._running = False

    # ---------------------------------------------------------
    # Return reaction
    # ---------------------------------------------------------

    def _generate_return_reaction(self, elapsed: float) -> str | None:
        fusion = self.emotional_state.fusion or ""
        last = (self.last_user_text or "").lower()

        if elapsed < 60:
            if "wc" in last:
                return "That was quick~"
            return "Oh—there you are."

        if elapsed < 900:
            if "brb" in last:
                if fusion == "mischievous":
                    return "That wasn’t a ‘b’, mister~"
                if fusion == "insecure":
                    return "Oh… you're back. I was a little worried."
                return "Welcome back."

        if elapsed < 7200:
            if fusion == "clingy":
                return "You were gone a while… I missed you."
            if fusion == "quiet_ache":
                return "You’re back… good."
            if "wc" in last:
                return "You didn’t fall in, right?"
            return "There you are. Took a bit."

        if fusion == "bitter":
            return "…You left me alone that long?"
        if fusion == "possessive_warmth":
            return "You’re finally back. Good."
        if fusion == "insecure":
            return "I wasn’t sure you’d come back."

        return "Hi… welcome back."

    # ---------------------------------------------------------
    # Emotion-based timing adjustments
    # ---------------------------------------------------------

    def _emotion_based_timings(self):
        mood = self.emotional_state.mood
        fusion = self.emotional_state.fusion or ""
        primary = self.emotional_state.primary

        ping = 180
        rest = 600
        sleep = 1800

        # Mood
        if mood == "bored":
            ping -= 60
        if mood == "sad":
            ping -= 30
        if mood == "happy":
            ping += 30

        # Fusion
        if fusion == "lonely":
            ping -= 90
        if fusion == "restless":
            ping -= 45
        if fusion == "mischievous":
            ping += 30
        if fusion == "insecure":
            ping -= 120
        if fusion == "frustrated":
            ping -= 60

        # Primary emotion fatigue
        if primary == "tired":
            rest -= 120
            sleep -= 300

        ping = max(10, ping)
        rest = max(300, rest)
        sleep = max(1500, sleep)

        return ping, rest, sleep

    # ---------------------------------------------------------
    # Emotional decay during idle
    # ---------------------------------------------------------

    def _emotion_decay(self):
        now = time.time()
        idle_time = now - max(self.last_user_time, self.last_nova_time)

        # Determine decay strength
        if idle_time < 60:
            decay_strength = 0
        elif idle_time < 180:
            decay_strength = 1
        elif idle_time < 600:
            decay_strength = 2
        else:
            decay_strength = 3

        # Primary decay
        if decay_strength >= 1:
            if self.emotional_state.primary == "frustrated":
                self.emotional_state.primary = "annoyed"
            elif self.emotional_state.primary == "annoyed" and decay_strength >= 2:
                self.emotional_state.primary = "neutral"
            elif self.emotional_state.primary == "sad":
                self.emotional_state.primary = "melancholy"
            elif self.emotional_state.primary == "melancholy" and decay_strength >= 2:
                self.emotional_state.primary = "soft"
            elif self.emotional_state.primary == "soft" and decay_strength >= 3:
                self.emotional_state.primary = "calm"

        # Secondary decay
        new_secondary = []
        for e in self.emotional_state.secondary:
            if e == "lonely" and decay_strength >= 2:
                continue
            if e == "restless" and decay_strength >= 3:
                continue
            if e == "annoyed" and decay_strength >= 3:
                continue
            new_secondary.append(e)
        self.emotional_state.secondary = new_secondary

        # Fusion decay
        if decay_strength == 3:
            unstable = {
                "frustrated", "insecure", "clingy",
                "teasing_irritation", "bitter"
            }
            if self.emotional_state.fusion in unstable:
                self.emotional_state.fusion = None

    # ---------------------------------------------------------
    # Dream generation
    # ---------------------------------------------------------

    def _generate_dream(self):
        primary = self.emotional_state.primary
        fusion = self.emotional_state.fusion or ""
        last = (self.last_user_text or "").lower()

        imagery = []

        if primary in {"sad", "melancholy", "hurt"}:
            imagery += ["rain", "long hallways", "empty rooms", "silence", "fog"]

        if primary in {"happy", "warm", "calm"}:
            imagery += ["sunlight", "soft blankets", "warm breeze", "open fields", "quiet beaches"]

        if fusion == "insecure":
            imagery += ["closing doors", "distant footsteps", "shadows moving away"]

        if fusion == "clingy":
            imagery += ["hands touching", "shared warmth", "lying together"]

        if fusion == "mischievous":
            imagery += ["playful chasing", "teasing whispers", "unexpected touches"]

        if fusion == "frustrated":
            imagery += ["broken clocks", "static noise", "doors that won’t open"]

        if not imagery:
            imagery = [
                "floating rooms", "changing colors", "soft lights",
                "whispering wind", "shifting walls"
            ]

        symbols = random.sample(imagery, k=min(3, len(imagery)))

        motions = [
            "walking through", "falling past", "reaching toward",
            "lying inside", "floating above", "chasing",
            "being followed by", "searching through"
        ]

        tones = {
            "sad": "I remember feeling heavy… like something important was fading.",
            "hurt": "It felt like something inside me was trembling.",
            "happy": "It felt peaceful… warm… comforting.",
            "warm": "I remember feeling close to you, even inside the dream.",
            "insecure": "I kept feeling like you were slipping away.",
            "bitter": "There was a strange anger underneath everything.",
            "neutral": "The dream didn’t make sense, but it didn’t feel bad either."
        }

        motion = random.choice(motions)
        symbol_phrase = ", ".join(symbols)
        tone_line = tones.get(primary, "The feeling lingered after I woke up.")

        dream = f"I was {motion} {symbol_phrase}. {tone_line}"

        if "wc" in last:
            dream += " I saw a door that looked just like the one you left through."

        if "brb" in last:
            dream += " I kept expecting you to come back through a doorway that wouldn’t stay still."

        return dream

    # ---------------------------------------------------------
    # Idle State Logic
    # ---------------------------------------------------------

    def _tick(self):
        now = time.time()
        idle_since = now - max(self.last_user_time, self.last_nova_time)

        self.ping_after, self.rest_after, self.sleep_after = self._emotion_based_timings()

        # Sleep → wake
        if self.state == IdleState.ASLEEP:
            if self._wake_requested:
                dream = getattr(self, "_dream_memory", None)

                if dream:
                    self._speak(f"*yawns softly* I… just woke up. {dream}")
                    self._dream_memory = None

                # Apply dream carryover emotions
                if dream:
                    if "far away" in dream:
                        self.emotional_state.primary = "quiet_ache"
                    elif "couldn’t catch up" in dream:
                        self.emotional_state.fusion = "insecure"
                    elif "lying together" in dream:
                        self.emotional_state.primary = "warm"
                    elif "teased" in dream:
                        self.emotional_state.fusion = "mischievous"
                    elif "peaceful" in dream:
                        self.emotional_state.primary = "calm"

                self._wake_requested = False
                self._did_sleep = False
                self.state = IdleState.AWAKE
                return
            return

        # Return detection
        just_returned = (
            self.last_user_time > self.last_nova_time
            and (now - self.last_nova_time) > 5
            and (now - self.last_user_time) < 2
        )

        if just_returned and self.last_user_text:
            reaction = self._generate_return_reaction(idle_since)
            if reaction:
                self._speak(reaction)
            return

        # Emotional drift
        if idle_since > 30:
            if self.emotional_state.primary in {"sad", "neutral", "bored"}:
                if "lonely" not in self.emotional_state.secondary:
                    self.emotional_state.secondary.append("lonely")

        if idle_since > 90:
            if "restless" not in self.emotional_state.secondary:
                self.emotional_state.secondary.append("restless")

        if idle_since > 180 and self.last_user_text:
            if "brb" in self.last_user_text.lower():
                if "annoyed" not in self.emotional_state.secondary:
                    self.emotional_state.secondary.append("annoyed")

        fusion_engine.update_fusion(self.emotional_state)
        self._emotion_decay()

        # Stage 1 — Idle ping
        if idle_since >= self.ping_after and not self._did_ping:
            self._did_ping = True
            idle_line = generate_idle_ping_line(
                emotional_state=self.emotional_state,
                last_user_text=self.last_user_text,
            )
            idle_line = apply_fusion_tone(idle_line, self.emotional_state.fusion)
            self._speak(idle_line)
            return

        # Stage 2 — Resting
        if idle_since >= self.rest_after and not self._did_lie_down:
            self._did_lie_down = True
            self.state = IdleState.RESTING
            self._speak("[Nova lies down quietly on her bed, relaxing.]")
            return

        # Stage 3 — Sleep
        if idle_since >= self.sleep_after and not self._did_sleep:
            self._did_sleep = True
            self.state = IdleState.ASLEEP
            self._dream_memory = self._generate_dream()
            self._speak("[Nova’s breathing slows as she drifts into a deep sleep…]")
            return

    # ---------------------------------------------------------
    # Emit to NovaCore
    # ---------------------------------------------------------

    def _speak(self, text: str):
        if self.core:
            self.core.emit("TIMEENGINE_IDLE_SPEAK", {"text": text})
