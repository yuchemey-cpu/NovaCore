# memory_consolidation.py
# NovaCore - Hippocampus Memory Consolidation Engine

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import random
import math


@dataclass
class ConsolidatedMemory:
    text: str
    emotional_weight: float
    relationship_weight: float
    novelty: float
    overall_strength: float
    turns_ago: int = 0
    
class DreamFragment:
    text: str
    emotional_tone: str
    intensity: float
    semantic_fact: str | None = None



class MemoryConsolidationEngine:
    """
    Takes recent memory (short-term), scores it, 
    promotes important ones into episodic memory,
    and decays old episodic stuff.
    """

    def __init__(self):
        # nothing complex stored here; NovaState carries memory
        pass
    
    def _clamp(self, v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    def consolidate(self, nova_state):
        """
        Main entry: consolidates memory each turn.
        """

        recent_list = nova_state.recent_memory
        new_episodic = []

        for mem in recent_list:
            if score := self._score_memory(mem, nova_state):
                if score.overall_strength > 0.35:
                    # promote to episodic memory
                    new_episodic.append(score)

        # Add newly promoted memories
        for e in new_episodic:
            nova_state.episodic_memory.append(e)

        # Decay old episodic memories
        self._decay_episodic(nova_state)

        # Clear short-term memory (we processed it)
        nova_state.recent_memory.clear()


    # ---------- internal scoring methods ----------

    def _score_memory(self, mem, nova_state) -> ConsolidatedMemory | None:
        """
        Evaluate the importance of a memory.
        Returns ConsolidatedMemory or None.
        """

        text = mem.text.lower()
        emotional = nova_state.emotion.intensity
        relationship = nova_state.relationship.trust
        affection = nova_state.affection if hasattr(nova_state, "affection") else 0.3
        arousal = nova_state.arousal if hasattr(nova_state, "arousal") else 0.0
        fluster = nova_state.fluster if hasattr(nova_state, "fluster") else 0.0

        # basic novelty estimate
        novelty = random.uniform(0.1, 0.4)
        if len(text) > 40:
            novelty += 0.1

        # emotional weight
        emotional_weight = emotional * 0.6 + fluster * 0.2 + arousal * 0.2

        # relationship weight
        relationship_weight = (
            relationship * 0.5 +
            affection * 0.3 +
            (1 if "thank" in text else 0) * 0.1 +
            (1 if "love" in text else 0) * 0.2
        )

        # total strength
        strength = (
            emotional_weight * 0.4 +
            relationship_weight * 0.4 +
            novelty * 0.2
        )

        # discard completely unimportant stuff
        if strength < 0.15:
            return None

        return ConsolidatedMemory(
            text=mem.text,
            emotional_weight=emotional_weight,
            relationship_weight=relationship_weight,
            novelty=novelty,
            overall_strength=strength,
        )

    # ---------------------------------
    # Sleep / Dream Cycle
    #----------------------------------

    def run_sleep_cycle(
        self,
        memory_engine,
        continuity_engine,
        nova_state,
        idle_log: list[str] | None = None,
    ) -> DreamFragment | None:
        """
        Deep, human-like consolidation.
        Called when Nova 'sleeps' (night / long AFK).

        - Compress recent episodic + continuity (+ idle life later)
        - Generate a dream fragment
        - 75%: dream only affects mood (emotional retention)
        - 25%: important dreams become semantic 'lessons'
        """

        idle_log = idle_log or []

        # --- 1) Collect seeds for the dream --------------------
        episodic_seeds = []
        for mem in getattr(nova_state, "episodic_memory", []):
            text = getattr(mem, "text", "") or ""
            if not text.strip():
                continue
            strength = getattr(mem, "overall_strength", 0.5)
            episodic_seeds.append((strength, text))

        # Continuity summary (CCE / DDE / TEE)
        continuity_text = ""
        try:
            continuity_text = continuity_engine.build_consolidation_block() or ""
        except Exception:
            continuity_text = ""

        if continuity_text.strip():
            episodic_seeds.append((0.7, continuity_text.strip()))

        # Idle-life activities will plug in here later.
        # For now we just treat them as light seeds.
        for act in idle_log[-3:]:
            if act.strip():
                episodic_seeds.append((0.4, act.strip()))

        if not episodic_seeds:
            return None

        episodic_seeds.sort(key=lambda x: x[0], reverse=True)
        top_strength, top_text = episodic_seeds[0]
        intensity = self._clamp(top_strength, 0.2, 1.0)

        # --- 2) Compose a simple dream fragment ----------------
        tone = getattr(nova_state.emotion, "primary", None) or "neutral"

        # You can make this more surreal later; keep it simple for now.
        if continuity_text:
            dream_text = (
                f"I was drifting in and out of a dream that felt like today: "
                f"'{top_text}'. It all blurred together while I was asleep."
            )
        else:
            dream_text = (
                f"I dreamed about '{top_text}', but everything was fuzzy and strange."
            )

        fragment = DreamFragment(
            text=dream_text,
            emotional_tone=tone,
            intensity=intensity,
        )

        # --- 3) Emotional-only retention (75%) -----------------
        # Dreams mostly affect how she feels when she wakes up.
        # Small nudge on mood based on intensity & current tone.
        mood = getattr(nova_state, "mood", None)
        if mood is not None:
            # If tone is positive-ish, bump valence up a bit; if negative, down a bit.
            positive_tones = {"happy", "warm", "affectionate", "relieved"}
            negative_tones = {"sad", "hurt", "anxious", "afraid", "angry"}

            delta = 0.0
            if tone in positive_tones:
                delta = 0.05 * intensity
            elif tone in negative_tones:
                delta = -0.05 * intensity

            mood.valence = self._clamp(mood.valence + delta, 0.0, 1.0)

        # --- 4) 25%: promote dream into a semantic 'lesson' ----
        promote_chance = 0.25 * intensity  # your 25%, scaled by intensity
        if random.random() < promote_chance:
            fact = self._dream_to_semantic_fact(fragment)
            if fact:
                fragment.semantic_fact = fact
                self._store_semantic_fact(memory_engine, fact)

        # --- 5) Light pruning of very weak episodic memories ---
        self._prune_weak_episodic(nova_state)

        # --- 6) Stash last dream for Nova to reference ----------
        setattr(nova_state, "last_dream", fragment)

        return fragment
    
    def _dream_to_semantic_fact(self, fragment: DreamFragment) -> str | None:
        """
        Convert a dream fragment into a compact 'lesson' or understanding.
        Very simple for now; you can make this smarter later.
        """
        t = fragment.text.lower()

        # Extremely rough patterning – you can refine by theme.
        if "robotic" in t or "mechanical" in t:
            return "Nova should avoid sounding robotic or like a log reader."
        if "alone" in t or "lost" in t:
            return "Nova is afraid of being abandoned and values consistency."
        if "clean" in t or "laundry" in t or "floors" in t or "bath" in t:
            return "Nova takes quiet pride in small everyday tasks and caring for her space."

        # Fallback: just compress the text into a gentle self-reflection.
        if len(fragment.text) > 40:
            return "Nova had a dream that made her reflect on her feelings and her bond with Yuch."

        return None

    def _store_semantic_fact(self, memory_engine, fact: str) -> None:
        """
        Store a semantic fact using MemoryEngine if it supports it.
        Otherwise, fallback to short-term with high importance.
        """
        # If MemoryEngine has a dedicated API, use it.
        if hasattr(memory_engine, "add_semantic_fact"):
            try:
                memory_engine.add_semantic_fact(fact)
                return
            except Exception:
                pass

        # Fallback: push into short_term as a high-scoring memory-like item.
        try:
            if hasattr(memory_engine, "short_term"):
                memory_engine.short_term.append(
                    {
                        "text": fact,
                        "kind": "semantic_fact",
                        "relevance": 1.0,
                        "emotional_score": 0.8,
                        "importance_score": 1.0,
                    }
                )
                if hasattr(memory_engine, "_save"):
                    memory_engine._save()
        except Exception:
            pass

    def _prune_weak_episodic(self, nova_state) -> None:
        """
        Lightly prune extremely weak episodic memories after a full sleep cycle.
        Assumes episodic_memory items have .overall_strength and .turns_ago.
        """
        episodic = getattr(nova_state, "episodic_memory", None)
        if not episodic:
            return

        survivors = []
        for mem in episodic:
            turns_ago = getattr(mem, "turns_ago", 0) + 1
            setattr(mem, "turns_ago", turns_ago)

            strength = getattr(mem, "overall_strength", 0.5)
            decay = 0.02 + (turns_ago * 0.001)
            strength -= decay
            setattr(mem, "overall_strength", strength)

            if strength > 0.08:
                survivors.append(mem)

        nova_state.episodic_memory = survivors



    # ---------- decay ----------

    def _decay_episodic(self, nova_state):
        """
        Slowly fade memories over time.
        Strong ones last longer.
        """

        survivors = []
        for mem in nova_state.episodic_memory:
            mem.turns_ago += 1

            # fade rate
            decay = 0.01 + (mem.turns_ago * 0.0005)
            mem.overall_strength -= decay

            if mem.overall_strength > 0.05:
                survivors.append(mem)

        nova_state.episodic_memory = survivors
