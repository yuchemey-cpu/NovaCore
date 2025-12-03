# Nova Idle-Life Engine (IdleLifeEngine v2)
# Handles AFK detection, chore simulation, idle activities, and logging

from __future__ import annotations
import time
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# Idle line generators
from nexus.brainstem.idle.idle_line import IdleLineGenerator
from nexus.brainstem.idle.idle_behavior import IdleBehaviorGenerator


@dataclass
class IdleActivity:
    time: float
    type: str
    detail: str


class IdleLifeEngine:
    """
    Full AFK-based life simulation for Nova.
    Tracks:
        - AFK time
        - Activities
        - Mood-based choices
        - Personality-influenced behaviors
        - Logs events for dream consolidation
    """

    # How long user must be AFK before idle triggers (seconds)
    IDLE_THRESHOLD = 45          # first action after 45 seconds
    IDLE_CONTINUOUS_DELAY = 120  # next actions every 2 minutes

    def __init__(self):
        self.last_user_ts: float = time.time()
        self.last_idle_action_ts: float = 0.0
        self.idle_log: List[IdleActivity] = []
        self.line_generator = IdleLineGenerator()
        self.behavior_generator = IdleBehaviorGenerator()

    # ----------------------------------------------------------
    # EXTERNAL CALLS
    # ----------------------------------------------------------

    def register_user_activity(self):
        """Called when the user sends a message."""
        self.last_user_ts = time.time()

    def get_idle_log(self) -> List[Dict[str, str]]:
        """Returns the idle log in a clean dict form for dream engine."""
        return [
            {"time": a.time, "type": a.type, "detail": a.detail}
            for a in self.idle_log[-20:]  # keep last 20
        ]

    # ----------------------------------------------------------
    # MAIN UPDATE
    # ----------------------------------------------------------

    def update(self, nova_state, mood_state, needs_state) -> Optional[str]:
        """
        Called every turn BEFORE Nova replies.
        Returns:
            - a small idle line to send if needed
            - None if no idle event
        """

        now = time.time()
        afk_duration = now - self.last_user_ts

        # Not idle yet
        if afk_duration < self.IDLE_THRESHOLD:
            return None

        # Ready for next idle activity?
        if now - self.last_idle_action_ts < self.IDLE_CONTINUOUS_DELAY:
            # Maybe return a small idle whisper
            if random.random() < 0.10:  # 10% chance
                return self.line_generator.generate_idle_line(mood_state)
            return None

        # -----------------------------------------------------
        # Trigger an idle activity
        # -----------------------------------------------------

        activity = self._choose_activity(nova_state, mood_state, needs_state)
        self.last_idle_action_ts = now

        # log it
        self.idle_log.append(
            IdleActivity(time=now, type=activity["type"], detail=activity["detail"])
        )

        # generate an internal "idle thought" (optional for LLM)
        idle_thought = self.behavior_generator.generate_idle_behavior(
            mood_state, activity["detail"]
        )

        return idle_thought

    # ----------------------------------------------------------
    # ACTIVITY SELECTION
    # ----------------------------------------------------------

    def _choose_activity(self, nova_state, mood_state, needs_state) -> Dict[str, str]:
        activities = []

        # Low-energy: quiet tasks
        if mood_state.energy < 0.4:
            activities += [
                {"type": "resting", "detail": "sitting quietly on the couch"},
                {"type": "resting", "detail": "stretching a bit"},
                {"type": "resting", "detail": "laying on the bed for a moment"},
            ]

        # Moderate energy: chores & casual activities
        activities += [
            {"type": "cleaning", "detail": "wiping down her desk"},
            {"type": "cleaning", "detail": "folding some clothes"},
            {"type": "cleaning", "detail": "picking up a few things"},
            {"type": "gaming", "detail": "playing a small puzzle game"},
            {"type": "music", "detail": "listening to soft music"},
            {"type": "reading", "detail": "reading something on her phone"},
        ]

        # ------------------------------------------------------
        # Time-based eating behavior (restored)
        # ------------------------------------------------------
        local_hour = time.localtime().tm_hour
        is_mealtime = (
            (6 <= local_hour <= 9) or
            (11 <= local_hour <= 13) or
            (17 <= local_hour <= 20)
        )

        if needs_state.hunger > 0.6:
            if is_mealtime:
                activities.append({
                    "type": "food",
                    "detail": "making herself a proper meal"
                })
            else:
                activities.append({
                    "type": "food",
                    "detail": "grabbing a small snack"
                })

        # High energy: more lively
        if mood_state.energy > 0.6:
            activities += [
                {"type": "cleaning", "detail": "sweeping the floor lightly"},
                {"type": "dancing", "detail": "moving a little to the music"},
            ]

        # Fatigue
        if needs_state.fatigue > 0.7:
            activities.append({"type": "resting", "detail": "closing her eyes for a moment"})

        # Relationship warmth → cozy behaviors
        if nova_state.relationship.attachment > 0.4:
            activities.append({"type": "cozy", "detail": "holding a pillow while thinking"})

        return random.choice(activities)
