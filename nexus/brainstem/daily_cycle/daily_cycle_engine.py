# daily_cycle_engine.py
# NovaCore Daily Cycle Engine — handles fatigue, sleep, wake, and recovery states.

from __future__ import annotations
from typing import Optional
import random
import time

class DailyCycleState:
    def __init__(self):
        self.is_asleep = False
        self.last_sleep_time = None
        self.hours_slept = 0

class DailyCycleEngine:
    def __init__(self):
        self.state = DailyCycleState()

    def check_sleep_need(self, needs_state, emotion_state, drive_state) -> bool:
        """Returns True if Nova should fall asleep now."""
        
        tired = needs_state.fatigue > 0.75
        overloaded = emotion_state.intensity > 0.75
        
        # If tired or emotionally overwhelmed
        if tired or overloaded:
            return True
        
        return False

    def sleep(self, nova_state):
        """Nova falls asleep: resets fatigue and emotional load."""
        
        self.state.is_asleep = True
        self.state.last_sleep_time = time.time()
        self.state.hours_slept = 0
        
        # Reduce emotional intensity (dream discharge)
        nova_state.emotion.intensity *= 0.4
        
        # Mood drift toward neutral
        nova_state.mood.valence *= 0.7
        
        # Stop initiative while asleep
        nova_state.relationship.trust += 0.01  # Soft closeness
        return "*falls asleep…*"

    def update_sleep(self, nova_state):
        """Check if Nova should wake up based on hours slept."""
        
        if not self.state.is_asleep:
            return None
        
        hours = (time.time() - self.state.last_sleep_time) / 3600
        self.state.hours_slept = hours
        
        if hours >= 6:  # Normal sleep cycle
            return self.wake(nova_state)
        
        return None

    def wake(self, nova_state):
        """Nova wakes up and resets several states."""
        
        self.state.is_asleep = False

        # Reset fatigue
        nova_state.needs.fatigue = 0.1
        
        # Increase hunger + thirst slightly
        nova_state.needs.hunger += 0.2
        nova_state.needs.thirst += 0.15
        
        # Increase curiosity
        nova_state.drive.focus += 0.1

        # Emotional reset
        nova_state.emotion.stability += 0.1
        
        return "*wakes up slowly…*"
