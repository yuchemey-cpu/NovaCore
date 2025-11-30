# Nova/Continuity/continuity_engine.py

from __future__ import annotations

import os
import json
import glob
import datetime
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ContinuitySnapshot:
    """Optional high-level continuity view for Nova."""
    yesterday_summary: str
    recent_arc: str
    dominant_trend: str
    session_count: int


class ContinuityEngine:
    """
    Phase 9 – Continuity Engine

    Reads recent session summaries from Memory/long_term/sessions
    and produces:
      - Yesterday's summary
      - Recent emotional arc (dominant emotion trend)
      - A continuity block for LlmBridge.build_context()
    """

    def __init__(self, sessions_dir: str):
        self.sessions_dir = sessions_dir

    # ------------------------------------------------------------
    # COMPATIBILITY LAYER (Phase 9 API expected by nova.py)
    # ------------------------------------------------------------
    def on_user_message(self, text: str):
        """Compatibility — accept user messages for future continuity use."""
        try:
            self.add_entry("user", text)
        except Exception:
            # Safe fallback: do nothing
            pass

    def on_nova_message(self, text: str):
        """Compatibility — accept Nova messages for future continuity use."""
        try:
            self.add_entry("nova", text)
        except Exception:
            # Safe fallback: do nothing
            pass

    def add_entry(self, speaker: str, text: str):
        """
        Minimal placeholder so nova.py doesn't crash.
        Phase 9 continuity doesn't actively record anything,
        so we only keep this for future expansion.
        """
        # You can later log these into a buffer or file.
        return
    

    # ------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------

    def _load_session_files(self) -> List[str]:
        """Return sorted list of session file paths (oldest → newest)."""
        pattern = os.path.join(self.sessions_dir, "*.json")
        files = glob.glob(pattern)
        files.sort()
        return files

    def _load_entries(self, path: str) -> List[Dict[str, Any]]:
        """Load one session file (may contain list or single dict)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []

    def _parse_date_from_filename(self, path: str) -> Optional[datetime.date]:
        """
        Expect filenames like 'YYYY-MM-DD.json'.
        Returns a date or None if parsing fails.
        """
        name = os.path.basename(path)
        base, _ = os.path.splitext(name)
        try:
            return datetime.datetime.strptime(base, "%Y-%m-%d").date()
        except Exception:
            return None

    # ------------------------------------------------------------
    # PUBLIC CONTINUITY API
    # ------------------------------------------------------------

    def get_yesterday_summary(self) -> str:
        """
        Returns a clean summary of what 'yesterday' felt like.
        If no sessions exist, or no entry for yesterday exists,
        fallback language is used.
        """
        files = self._load_session_files()
        if not files:
            return "Nova doesn't remember any previous days yet."

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        summaries: List[str] = []
        for path in files:
            d = self._parse_date_from_filename(path)
            if d != yesterday:
                continue
            for entry in self._load_entries(path):
                text = (entry.get("summary") or "").strip()
                if text:
                    summaries.append(text)

        if not summaries:
            # Use latest session as fallback
            latest_path = files[-1]
            entries = self._load_entries(latest_path)
            if not entries:
                return "Nova's sense of yesterday is still blank."

            text = (entries[-1].get("summary") or "").strip()
            if not text:
                return "Nova's sense of yesterday is still forming."

            return (
                "Nova doesn't have a clear memory of 'yesterday', "
                f"but the most recent day felt like this: {text}"
            )

        if len(summaries) == 1:
            return f"Yesterday felt like this: {summaries[0]}"
        else:
            joined = " ".join(summaries)
            return f"Yesterday had multiple moments. Overall it felt like: {joined}"

    def get_recent_arc(self, max_days: int = 7) -> tuple[str, str, int]:
        """
        Analyze several recent days and return:
          - arc_text: a readable description of recent emotional pattern
          - dominant: the dominant emotional trend
          - session_count: number of sessions considered
        """
        files = self._load_session_files()
        if not files:
            return ("Nova has no past days to look back on yet.", "neutral", 0)

        today = datetime.date.today()
        earliest = today - datetime.timedelta(days=max_days)

        emotion_counts: Dict[str, float] = {}
        session_count = 0

        for path in files:
            d = self._parse_date_from_filename(path)
            if d is None or d < earliest:
                continue

            entries = self._load_entries(path)
            if not entries:
                continue

            for e in entries:
                dom = (e.get("dominant_emotion") or "neutral") or "neutral"
                weight = float(e.get("overall_weight", 1.0))
                emotion_counts[dom] = emotion_counts.get(dom, 0.0) + weight
                session_count += 1

        if not emotion_counts or session_count == 0:
            return ("Recent days feel quiet and undefined so far.", "neutral", 0)

        # Determine dominant trend
        dominant = max(emotion_counts.items(), key=lambda x: x[1])[0]

        # English descriptions per emotion
        def describe(em):
            match em:
                case "happy":
                    return "mostly bright and uplifting"
                case "nostalgic":
                    return "soft and reflective"
                case "sad":
                    return "a bit heavy and quiet"
                case "fear":
                    return "tense and cautious"
                case "angry":
                    return "sharp and unsettled"
                case "excited":
                    return "energetic and lively"
                case "tired":
                    return "slow and drained"
                case "bored":
                    return "flat and uneventful"
                case _:
                    return "fairly steady and neutral"

        description = describe(dominant)

        arc_text = (
            f"Looking back over the last few days, things have felt {description}. "
            f"Nova's emotional trend with Yuch has been mostly '{dominant}'."
        )

        return (arc_text, dominant, session_count)

    def build_continuity_block(self, max_days: int = 7) -> str:
        """
        Build the text block that LlmBridge inserts into the full prompt.
        """
        yesterday = self.get_yesterday_summary()
        arc_text, dominant, count = self.get_recent_arc(max_days=max_days)

        if count == 0:
            return (
                "Continuity:\n"
                f"- Yesterday: {yesterday}\n"
                "- Recent arc: (no past days available)\n"
            )

        return (
            "Continuity:\n"
            f"- Yesterday: {yesterday}\n"
            f"- Recent arc ({min(count, max_days)} sessions): {arc_text}\n"
        )
