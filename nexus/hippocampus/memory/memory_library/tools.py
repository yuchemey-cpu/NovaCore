# MemoryLibrary/tools.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import time
import math
import random


# ---------------------------------------------------------
# Dataclasses for clean structured memory
# ---------------------------------------------------------

@dataclass
class EpisodicMemory:
    id: str
    ts: float
    date: str
    summary: str
    details: str
    emotions: List[str]
    tags: List[str]
    importance: float
    recall_count: int = 0
    last_recalled: Optional[float] = None


@dataclass
class SemanticMemory:
    key: str
    value: Any
    importance: float
    stable: bool
    created_at: float
    last_updated: float
    recall_count: int = 0
    last_recalled: Optional[float] = None


@dataclass
class EmotionalEvent:
    ts: float
    emotion: str
    intensity: float
    context: str
    episodic_id: Optional[str] = None


# ---------------------------------------------------------
# Memory Library
# ---------------------------------------------------------

class MemoryLibrary:
    """
    Advanced human-like memory system for Nova.

    - Episodic: experiences with Yuch (life story)
    - Semantic: facts, preferences, stable knowledge
    - Emotional: emotional history & reinforcement
    - System: internal flags & config
    - Short-term: working memory (last few messages / context)

    All reads/writes are buffered and flushed explicitly via save().
    """

    def __init__(self, base_dir: str | Path):
        self.base_path = Path(base_dir)

        self.ep_path = self.base_path / "episodic.json"
        self.sem_path = self.base_path / "semantic.json"
        self.em_path = self.base_path / "emotional.json"
        self.sys_path = self.base_path / "system.json"
        self.stm_path = self.base_path / "short_term.json"

        self.episodic: List[EpisodicMemory] = []
        self.semantic: Dict[str, SemanticMemory] = {}
        self.emotional: List[EmotionalEvent] = []
        self.system: Dict[str, Any] = {}
        self.short_term: Dict[str, Any] = {}

        self._loaded = False

    # -----------------------------------------------------
    # Disk I/O
    # -----------------------------------------------------

    def load(self) -> None:
        """Load all memory files from disk (idempotent)."""
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Episodic
        if self.ep_path.exists():
            raw = json.loads(self.ep_path.read_text(encoding="utf-8") or "[]")
            self.episodic = [EpisodicMemory(**item) for item in raw]
        else:
            self.episodic = []

        # Semantic
        if self.sem_path.exists():
            raw = json.loads(self.sem_path.read_text(encoding="utf-8") or "[]")
            self.semantic = {
                item["key"]: SemanticMemory(**item) for item in raw
            }
        else:
            self.semantic = {}

        # Emotional
        if self.em_path.exists():
            raw = json.loads(self.em_path.read_text(encoding="utf-8") or "[]")
            self.emotional = [EmotionalEvent(**item) for item in raw]
        else:
            self.emotional = []

        # System
        if self.sys_path.exists():
            self.system = json.loads(self.sys_path.read_text(encoding="utf-8") or "{}")
        else:
            self.system = {}

        # Short-term
        if self.stm_path.exists():
            self.short_term = json.loads(self.stm_path.read_text(encoding="utf-8") or "{}")
        else:
            self.short_term = {}

        self._loaded = True

    def save(self) -> None:
        """Flush all memory collections to disk."""
        if not self._loaded:
            # nothing to save yet
            return

        self.ep_path.write_text(
            json.dumps([asdict(e) for e in self.episodic], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.sem_path.write_text(
            json.dumps([asdict(s) for s in self.semantic.values()], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.em_path.write_text(
            json.dumps([asdict(e) for e in self.emotional], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.sys_path.write_text(
            json.dumps(self.system, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.stm_path.write_text(
            json.dumps(self.short_term, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # -----------------------------------------------------
    # Short-term memory (working memory)
    # -----------------------------------------------------

    def set_short_term(self, key: str, value: Any) -> None:
        """
        Store something in working memory, not meant to last forever.
        Example keys:
          - "last_topic"
          - "last_user_messages"
          - "last_nova_messages"
          - "current_task"
        """
        self.short_term[key] = {
            "value": value,
            "ts": time.time(),
        }

    def get_short_term(self, key: str, default: Any = None) -> Any:
        entry = self.short_term.get(key)
        if not entry:
            return default
        return entry.get("value", default)

    # -----------------------------------------------------
    # Semantic memory (facts)
    # -----------------------------------------------------

    def remember_fact(
        self,
        key: str,
        value: Any,
        importance: float = 0.7,
        stable: bool = True,
    ) -> None:
        """
        Store or update a semantic fact.
        Example:
          remember_fact("user_name", "Yuch", importance=0.95, stable=True)
        """
        now = time.time()
        importance = float(max(0.0, min(1.0, importance)))

        existing = self.semantic.get(key)
        if existing:
            existing.value = value
            existing.importance = max(existing.importance, importance)
            existing.stable = existing.stable or stable
            existing.last_updated = now
        else:
            self.semantic[key] = SemanticMemory(
                key=key,
                value=value,
                importance=importance,
                stable=stable,
                created_at=now,
                last_updated=now,
            )

    def recall_fact(self, key: str, default: Any = None) -> Any:
        entry = self.semantic.get(key)
        if not entry:
            return default

        entry.recall_count += 1
        entry.last_recalled = time.time()
        return entry.value

    def find_facts(self, prefix: str, min_importance: float = 0.4) -> Dict[str, Any]:
        """
        Return a dict of facts where key starts with prefix.
        Useful for pulling user-related knowledge, etc.
        """
        out: Dict[str, Any] = {}
        for key, mem in self.semantic.items():
            if not key.startswith(prefix):
                continue
            if mem.importance < min_importance:
                continue
            out[key] = mem.value
        return out

    def top_facts(self, limit: int = 5) -> Dict[str, Any]:
        """
        Return a few of the most important facts, for building LLM context.
        """
        items = sorted(
            self.semantic.values(),
            key=lambda m: (m.importance, m.recall_count),
            reverse=True,
        )
        return {m.key: m.value for m in items[:limit]}

    # -----------------------------------------------------
    # Episodic memory (experiences)
    # -----------------------------------------------------

    def add_episodic(
        self,
        summary: str,
        details: str = "",
        emotions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        ts: Optional[float] = None,
    ) -> EpisodicMemory:
        """
        Create a new episodic memory entry.
        Called at the end of a meaningful moment or session.
        """
        now = ts if ts is not None else time.time()
        importance = float(max(0.0, min(1.0, importance)))

        # Emotion amplifies importance a bit
        if emotions:
            strong = {"sad", "hurt", "afraid", "angry", "nostalgic", "happy"}
            if any(e in strong for e in emotions):
                importance = min(1.0, importance + 0.15)

        eid = f"e_{int(now)}_{random.randint(0, 9999)}"
        date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(now))

        mem = EpisodicMemory(
            id=eid,
            ts=now,
            date=date_str,
            summary=summary.strip(),
            details=details.strip(),
            emotions=emotions or [],
            tags=tags or [],
            importance=importance,
        )
        self.episodic.append(mem)
        return mem

    def _episodic_score(
        self,
        mem: EpisodicMemory,
        query: str,
        emotion_bias: Optional[str],
    ) -> float:
        """
        Compute how relevant an episodic memory is to the query,
        with optional bias toward a specific emotion.
        """
        q = query.lower().strip()
        if not q:
            base = 0.1
        else:
            text = (mem.summary + " " + mem.details + " " + " ".join(mem.tags)).lower()
            # crude keyword overlap
            matches = 0
            for word in q.split():
                if word in text:
                    matches += 1
            base = matches / (len(q.split()) + 1)

        # importance & recency bonus
        age_days = max(0.0, (time.time() - mem.ts) / 86400.0)
        recency = 1.0 / (1.0 + age_days)  # 1.0 -> now, dropping over time
        importance = mem.importance

        score = base * 0.5 + recency * 0.25 + importance * 0.25

        # emotion bias
        if emotion_bias and mem.emotions:
            if emotion_bias in mem.emotions:
                score *= 1.3

        return score

    def recall_episodic(
        self,
        query: str = "",
        emotion_bias: Optional[str] = None,
        limit: int = 3,
        min_score: float = 0.15,
    ) -> List[EpisodicMemory]:
        """
        Return a small set of episodic memories relevant to the current situation.
        This is what you feed into LlmBridge as context.
        """
        if not self.episodic:
            return []

        scored: List[Tuple[float, EpisodicMemory]] = []
        for mem in self.episodic:
            s = self._episodic_score(mem, query, emotion_bias)
            if s < min_score:
                continue
            scored.append((s, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [m for _, m in scored[:limit]]

        now = time.time()
        for mem in selected:
            mem.recall_count += 1
            mem.last_recalled = now

        return selected

    # -----------------------------------------------------
    # Emotional history
    # -----------------------------------------------------

    def record_emotion_event(
        self,
        emotion: str,
        intensity: float,
        context: str,
        episodic_id: Optional[str] = None,
    ) -> None:
        """
        Log an emotional moment, optionally linked to an episodic memory.
        """
        ev = EmotionalEvent(
            ts=time.time(),
            emotion=emotion,
            intensity=float(max(0.0, min(1.0, intensity))),
            context=context.strip(),
            episodic_id=episodic_id,
        )
        self.emotional.append(ev)

    def recent_emotional_trend(self, window_seconds: int = 86400) -> Dict[str, float]:
        """
        Return a simple distribution of emotions over the recent window.
        Useful for continuity summary ("these days we've been mostly...").
        """
        cutoff = time.time() - window_seconds
        counts: Dict[str, float] = {}
        total = 0.0
        for ev in self.emotional:
            if ev.ts < cutoff:
                continue
            counts[ev.emotion] = counts.get(ev.emotion, 0.0) + ev.intensity
            total += ev.intensity

        if total <= 0:
            return {}

        return {k: v / total for k, v in counts.items()}

    # -----------------------------------------------------
    # Decay / forgetting
    # -----------------------------------------------------

    def run_decay(self) -> None:
        """
        Apply forgetting rules.
        Called maybe once per day (on shutdown or wake).
        """
        now = time.time()

        # Episodic: drop very old, low-importance, never-recalled memories
        keep_episodic: List[EpisodicMemory] = []
        for mem in self.episodic:
            age_days = (now - mem.ts) / 86400.0

            # Hard keep deeply important memories
            if mem.importance >= 0.85:
                keep_episodic.append(mem)
                continue

            # If never recalled, low importance, and old → drop
            if mem.recall_count == 0 and mem.importance < 0.4 and age_days > 14:
                continue

            # Soft decay of importance over time
            if age_days > 7 and mem.importance > 0.3:
                mem.importance *= 0.98

            keep_episodic.append(mem)

        self.episodic = keep_episodic

        # Semantic: forget non-stable, low-importance, unused facts
        to_delete: List[str] = []
        for key, mem in self.semantic.items():
            if mem.stable:
                continue

            age_days = (now - mem.created_at) / 86400.0
            last_used_days = (
                (now - mem.last_recalled) / 86400.0
                if mem.last_recalled
                else age_days
            )

            if mem.importance < 0.3 and age_days > 14 and last_used_days > 7:
                to_delete.append(key)
            elif age_days > 7 and mem.importance > 0.3:
                mem.importance *= 0.99

        for key in to_delete:
            self.semantic.pop(key, None)

        # Short-term: flush very old working memory
        new_stm: Dict[str, Any] = {}
        for key, entry in self.short_term.items():
            ts = entry.get("ts", now)
            if now - ts > 3600:  # older than 1 hour
                continue
            new_stm[key] = entry
        self.short_term = new_stm

    # -----------------------------------------------------
    # Helper: build context for LLM
    # -----------------------------------------------------

    def build_context_snippet(
        self,
        last_user_text: str,
        primary_emotion: Optional[str],
        limit_episodic: int = 3,
        limit_facts: int = 5,
    ) -> Dict[str, Any]:
        """
        High-level helper: return a small dict that LlmBridge can turn into text
        for the system prompt / hidden context.
        """
        episodic_mem = self.recall_episodic(
            query=last_user_text,
            emotion_bias=primary_emotion,
            limit=limit_episodic,
        )

        facts = self.top_facts(limit=limit_facts)

        return {
            "episodic": [
                {
                    "date": m.date,
                    "summary": m.summary,
                    "emotions": m.emotions,
                    "importance": round(m.importance, 2),
                }
                for m in episodic_mem
            ],
            "facts": facts,
        }
