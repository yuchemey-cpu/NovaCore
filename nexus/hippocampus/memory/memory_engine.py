# Nova/Memory/memory_engine.py (Purified & Upgraded for Phase 10)

from __future__ import annotations

import os
import json
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ======================================================================
# RAW EVENTS — Real short-term "experience" for the session
# ======================================================================

@dataclass
class RawEvent:
    turn: int
    speaker: str            # "user" / "nova"
    text: str
    emotion: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5


# ======================================================================
# EPISODIC MEMORY — Consolidated memories stored long-term
# ======================================================================

@dataclass
class EpisodicMemory:
    id: str
    date: str
    summary: str
    topics: List[str]
    emotional_tone: str
    importance: float
    tags: List[str]


# ======================================================================
# MEMORY ENGINE (Purified)
# ======================================================================

class MemoryEngine:
    """
    Phase 10 Memory Engine

    Handles:
      - Raw short-term session events
      - Episodic memory creation (consolidation)
      - Daily diary summaries (kept from your old engine)
      - Semantic memory search (new)
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.short_term: List[RawEvent] = []
        self.turn_counter = 0

    # ------------------------------------------------------------------
    # RECORDING (session buffer)
    # ------------------------------------------------------------------

    def on_user_message(self, text: str, emotion: Optional[str] = None):
        self.turn_counter += 1
        self._record("user", text, emotion)

    def on_nova_message(self, text: str, emotion: Optional[str] = None):
        self._record("nova", text, emotion)

    def _record(self, speaker: str, text: str, emotion: Optional[str]):
        """
        Store raw conversational material for consolidation.
        """
        ev = RawEvent(
            turn=self.turn_counter,
            speaker=speaker,
            text=text,
            emotion=emotion,
            importance=0.5
        )
        self.short_term.append(ev)

    # ------------------------------------------------------------------
    # CONSOLIDATION (end-of-session)
    # ------------------------------------------------------------------

    def consolidate_session(self) -> List[EpisodicMemory]:
        """
        Turn the short-term buffer into episodic memories.
        This is your true Memory Consolidation.
        """
        if not self.short_term:
            return []

        today = datetime.date.today().isoformat()

        summary = self._summarize_session(self.short_term)
        emotional_tone = self._infer_emotional_tone(self.short_term)
        topics = self._infer_topics(self.short_term)

        ep = EpisodicMemory(
            id=f"{today}-{len(self.short_term)}",
            date=today,
            summary=summary,
            topics=topics,
            emotional_tone=emotional_tone,
            importance=0.7,
            tags=["session"]
        )

        self._save_episodic(ep)
        self.short_term.clear()

        return [ep]

    def _summarize_session(self, events: List[RawEvent]) -> str:
        """
        Create a compact human-friendly sentence about the session.
        """
        user_lines = [e.text for e in events if e.speaker == "user"]
        if not user_lines:
            return "A quiet session with little conversation."

        first = user_lines[0][:80]
        return f"A session where Yuch began by saying: '{first}...'"

    def _infer_emotional_tone(self, events: List[RawEvent]) -> str:
        emos = [e.emotion for e in events if e.emotion]
        if not emos:
            return "neutral"
        return emos[-1]  # last emotional tone for now

    def _infer_topics(self, events: List[RawEvent]) -> List[str]:
        """
        Naive keyword→topic system (replace later with semantic tagging).
        """
        text = " ".join(e.text.lower() for e in events)
        topics = []

        if "nova" in text or "engine" in text:
            topics.append("nova_core")

        if "chips" in text or "snack" in text:
            topics.append("snacks")

        if "memory" in text or "consolidation" in text:
            topics.append("memory_work")

        return topics or ["general"]

    # ------------------------------------------------------------------
    # STORAGE
    # ------------------------------------------------------------------

    def _save_episodic(self, mem: EpisodicMemory):
        """
        Append episodic memories into daily JSON file.
        """
        day_path = os.path.join(self.base_dir, f"{mem.date}.json")
        data = []

        if os.path.exists(day_path):
            try:
                with open(day_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []

        data.append(mem.__dict__)

        with open(day_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # RETRIEVAL (semantic episodic recall)
    # ------------------------------------------------------------------

    def get_relevant_episodic(self, query: str, limit: int = 2) -> List[str]:
        """
        Return 1–2 most relevant episodic summaries for context.
        """
        today = datetime.date.today()
        all_paths = []

        # scan up to 14 days back
        for i in range(14):
            d = today - datetime.timedelta(days=i)
            path = os.path.join(self.base_dir, f"{d.isoformat()}.json")
            if os.path.exists(path):
                all_paths.append(path)

        mems: List[EpisodicMemory] = []

        for path in all_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                for obj in arr:
                    mems.append(EpisodicMemory(**obj))
            except Exception:
                pass

        scored = []
        q = query.lower()

        for m in mems:
            score = 0.0
            blob = (m.summary + " " + " ".join(m.topics)).lower()
            for w in q.split():
                if w in blob:
                    score += 1.0
            score += m.importance * 0.5

            if score > 0:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m.summary for (s, m) in scored[:limit]]

    # ------------------------------------------------------------------
    # DAILY SUMMARY (kept from your old engine)
    # ------------------------------------------------------------------

    def save_daily_summary(self, text: str, dominant_emotion: str, weight: float):
        """
        Daily diary entry — preserved from original engine.
        """
        today = datetime.date.today().isoformat()
        file_path = os.path.join(self.base_dir, f"{today}_summary.json")

        entry = {
            "summary": text,
            "dominant_emotion": dominant_emotion,
            "weight": weight
        }

        data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data.append(entry)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
