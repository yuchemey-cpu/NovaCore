# memory_engine.py (diary-style version)

import json
import os
import time
import datetime
import glob
from typing import List, Dict, Any
from nexus.hippocampus.memory.config import MEMORY_FILE, SESSIONS_DIR


class MemoryEngine:

    def __init__(self, path: str = None, emotional_state=None):
        """
        emotional_state is passed in from nova.py (global heart).
        If None, we fall back to neutral behavior.
        """
        self.path = path or MEMORY_FILE
        self.emotional_state = emotional_state
        self.memories: List[Dict[str, Any]] = []
        self.short_term: List[Dict[str, Any]] = []  # in-session buffer
        self.max_short_memory = 100
        self._load()

    def _load(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.memories = data.get("memories", [])
            except Exception:
                self.memories = []
        else:
            self.memories = []

    def _save(self):
        data = {"memories": self.memories}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _topic_key(self, text: str) -> str:
        t = text.lower()
        for ch in [".", ",", "!", "?", ";", ":"]:
            t = t.replace(ch, " ")
        words = [w for w in t.split() if w not in {"the", "a", "an", "and", "with", "of", "to"}]
        return " ".join(words[:4])

    def _compress_text(self, base_text: str, count: int) -> str:
        base_text = base_text.strip().capitalize()
        if count == 1:
            return base_text
        elif count == 2:
            return f"I remember you mentioned before: '{base_text}'."
        elif 3 <= count <= 4:
            return f"This came up a few times — '{base_text}' still stands out to me."
        else:
            return f"I still recall something about it — '{base_text}', though it's a bit fuzzy now."

    def _evaluate_importance(self, text: str, base_importance: float) -> float:
        text_lower = text.lower()
        relevance_cues = ["remember", "note", "mark this", "lesson", "test", "result", "truth"]
        personal_refs = ["you", "yuch", "nova", "we", "our"]
        factual_clues = ["because", "means", "is when", "is how", "definition", "explains"]

        score = base_importance
        if any(w in text_lower for w in relevance_cues):
            score += 0.3
        if any(w in text_lower for w in personal_refs):
            score += 0.1
        if any(w in text_lower for w in factual_clues):
            score += 0.15
        return min(score, 1.0)

    def add_memory(self, text: str, importance: float = 0.5) -> None:
        """
        Add a memory with:
        - topic merging
        - emotional weighting
        - short-term buffer + long-term store
        """
        importance = self._evaluate_importance(text, importance)
        now = time.time()
        topic = self._topic_key(text)

        # Emotion → importance multiplier (using injected emotional_state)
        primary = getattr(self.emotional_state, "primary", "neutral") if self.emotional_state else "neutral"
        emotion_weights = {
            "fear": 1.8,
            "sad": 1.5,
            "angry": 1.6,
            "nostalgic": 1.4,
            "excited": 1.3,
            "happy": 1.2,
            "calm": 1.0,
            "neutral": 1.0,
            "tired": 0.6,
            "bored": 0.2,
        }
        weight = emotion_weights.get(primary, 1.0)

        # final importance after emotional influence
        importance = importance * weight
        importance = max(0.1, min(importance, 2.0))  # clamp to safe range

        # short-term buffer (for in-session recall)
        self.short_term.append({"text": text, "importance": importance})
        self.short_term = self.short_term[-self.max_short_memory:]

        # merge into long-term memory list
        for mem in self.memories:
            if mem.get("topic_key") == topic:
                mem["count"] = mem.get("count", 1) + 1
                mem["last_seen"] = now
                mem["importance"] = max(mem.get("importance", 0.0), importance)
                base = mem.get("original_text", mem.get("text", text))
                mem["original_text"] = base
                mem["text"] = self._compress_text(base, mem["count"])
                self._save()
                return

        new_mem = {
            "topic_key": topic,
            "text": text.strip(),
            "original_text": text.strip(),
            "created_at": now,
            "last_seen": now,
            "count": 1,
            "importance": float(importance),
        }
        self.memories.append(new_mem)
        self._maybe_prune()
        self._save()

    def _maybe_prune(self, max_memories: int = 200) -> None:
        if len(self.memories) <= max_memories:
            return
        self.memories.sort(key=lambda m: (m.get("importance", 0.0), m.get("last_seen", 0.0)))
        self.memories = self.memories[-max_memories:]

    # ---------- NEW: summaries helper (this was missing) ----------

    def get_summaries(self, limit: int = 5) -> List[str]:
        """
        Returns the top N important / recent memory texts.
        Used for daily diary-style summaries.
        """
        if not self.memories:
            return []
        ordered = sorted(
            self.memories,
            key=lambda m: (m.get("importance", 0.0), m.get("last_seen", 0.0)),
            reverse=True,
        )
        return [m.get("text", "").strip() for m in ordered[:limit]]

    # ---------- Diary-style session summarization ----------

    def save_session_summary(self) -> str | None:
        """
        Save session summary to SESSIONS_DIR as a dated JSON file.
        Adds emotionally-aware dominant_emotion and overall_weight.
        """
        if not self.memories and not self.short_term:
            return None
        os.makedirs(SESSIONS_DIR, exist_ok=True)

        highlights = self.get_summaries(limit=5)
        summary_text = self._build_narrative_summary(highlights)

        # Determine dominant emotion of the day from injected state
        dominant = getattr(self.emotional_state, "primary", "neutral") if self.emotional_state else "neutral"

        # Emotional weight curve (how “strong” this day will be)
        emotion_day_weight = {
            "fear": 1.3,
            "sad": 1.25,
            "angry": 1.2,
            "nostalgic": 1.35,
            "excited": 1.3,
            "happy": 1.2,
            "calm": 1.0,
            "neutral": 1.0,
            "tired": 0.8,
            "bored": 0.6,
        }
        overall_weight = emotion_day_weight.get(dominant, 1.0)

        entry = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "summary": summary_text,
            "liked": [],
            "disliked": [],
            "dominant_emotion": dominant,
            "overall_weight": overall_weight,
        }

        filename = datetime.datetime.now().strftime("%Y-%m-%d") + ".json"
        path = os.path.join(SESSIONS_DIR, filename)

        data = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data = [data]
            except Exception:
                data = []

        data.append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def _build_narrative_summary(self, highlights: List[str]) -> str:
        """
        Builds an emotionally-aware summary of the day.
        Tone adjusts based on Nova's current emotional state.
        """
        primary = getattr(self.emotional_state, "primary", "neutral") if self.emotional_state else "neutral"

        if not highlights:
            return "It was a quiet day."

        sentences = [h.strip().capitalize() for h in highlights if len(h.strip()) > 3]
        core_text = ". ".join(sentences)
        date_str = datetime.datetime.now().strftime("%B %d, %Y")

        tone = {
            "happy":     "It felt like a bright, uplifting day.",
            "excited":   "There was a lively, spirited energy today.",
            "nostalgic": "The day had a warm, reflective feeling to it.",
            "sad":       "The day felt a bit heavy and quiet.",
            "fear":      "The day carried a tense, cautious undertone.",
            "angry":     "The day had a sharp, unsettled tone.",
            "tired":     "Everything felt slower and softer today.",
            "bored":     "Nothing stood out much today.",
            "calm":      "The day felt peaceful and steady.",
            "neutral":   "",
        }

        mood_sentence = tone.get(primary, "")
        if mood_sentence:
            return f"On {date_str}, {mood_sentence} We talked about: {core_text}."
        else:
            return f"On {date_str}, we talked about: {core_text}."

    def get_latest_session_summary(self) -> str:
        session_files = sorted(glob.glob(os.path.join(SESSIONS_DIR, "*.json")), reverse=True)
        if not session_files:
            return ""
        latest_path = session_files[0]
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data[-1].get("summary", "")
            elif isinstance(data, dict):
                return data.get("summary", "")
            return ""
        except Exception:
            return ""

    def search_memories(self, query: str) -> List[str]:
        """
        Search short-term + long-term memories with emotional filtering bias.
        Hybrid model:
        - Emotionally relevant memories rise to the top.
        - High-importance memories can override emotional bias.
        - Nothing is discarded.
        """
        primary = getattr(self.emotional_state, "primary", "neutral") if self.emotional_state else "neutral"

        emotion_map = {
            "sad":        ["comfort", "support", "safe", "care", "kind", "gentle", "soft"],
            "nostalgic":  ["past", "memory", "old times", "warm", "special", "together"],
            "fear":       ["danger", "risk", "warning", "caution", "hurt", "threat"],
            "angry":      ["argument", "conflict", "frustration", "upset"],
            "happy":      ["fun", "joy", "laugh", "good", "excited", "smile"],
            "excited":    ["new", "idea", "plan", "future", "energy"],
            "curious":    ["why", "how", "learn", "explore"],
            "tired":      ["slow", "rest", "quiet"],
            "bored":      ["nothing", "empty", "tired"],
            "calm":       [],
            "neutral":    [],
        }
        emotional_keywords = emotion_map.get(primary, [])

        combined = []

        # short-term
        for item in self.short_term:
            combined.append({
                "text": item.get("text", ""),
                "importance": item.get("importance", 0.5),
                "dominant_emotion": None,
                "source": "short",
            })

        # merged long-term
        for mem in self.memories:
            combined.append({
                "text": mem.get("text", ""),
                "importance": mem.get("importance", 0.5),
                "dominant_emotion": mem.get("dominant_emotion"),
                "source": "merged",
            })

        # daily diary files
        session_files = sorted(glob.glob(os.path.join(SESSIONS_DIR, "*.json")), reverse=True)
        for path in session_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                for e in entries:
                    combined.append({
                        "text": e.get("summary", ""),
                        "importance": e.get("overall_weight", 0.5),
                        "dominant_emotion": e.get("dominant_emotion"),
                        "source": "daily",
                    })
            except Exception:
                continue

        scored = []
        q = query.lower()
        for mem in combined:
            text = (mem.get("text") or "").lower()
            importance_score = float(mem.get("importance", 0.5))

            tokens = [t for t in q.split() if t]
            if not tokens:
                relevance = 0.0
            else:
                matches = sum(1 for t in tokens if t in text)
                relevance = matches / len(tokens)

            emotional_score = sum(1 for w in emotional_keywords if w in text)

            dom = mem.get("dominant_emotion")
            dom_boost = 1.0
            if dom and dom == primary:
                dom_boost = 1.3

            score = (relevance * 1.5) + (emotional_score * 1.4) + (importance_score * 1.2)
            score *= dom_boost

            scored.append((score, mem.get("text", "")))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:5]]

    def clear_short_term(self):
        """Safely clears short-term memory after transfer."""
        self.short_term = []
        self._save()
