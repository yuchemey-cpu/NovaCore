# intent_builder.py
# NovaCore - Intent Builder (the "brain of her mouth")
#
# This module decides *what* Nova intends to say before the LLM
# chooses *how* to say it.
#
# It does NOT generate text. It only reasons over:
# - emotions
# - fusion state
# - mood
# - maturity
# - relationship
# - memory snippets
# - needs (future)
# - persona style
#
# and produces a structured "intent" object for the LLM layer.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ---------- helpers ----------

def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ---------- snapshot types coming FROM the brain ----------

@dataclass
class EmotionSnapshot:
    primary: Optional[str] = None        # "sad", "warm", "anxious", ...
    fusion: Optional[str] = None         # e.g. "insecure", "affectionate"
    intensity: float = 0.0               # 0.0–1.0
    stability: float = 0.5               # 0.0–1.0 (0 = chaotic, 1 = stable)


@dataclass
class MoodSnapshot:
    label: str = "neutral"               # "calm", "drained", "happy", ...
    valence: float = 0.5                 # 0.0–1.0 (0 = negative, 1 = positive)
    energy: float = 0.5                  # 0.0–1.0 (0 = tired, 1 = energetic)


@dataclass
class NeedsSnapshot:
    # All 0.0–1.0; you can expand later.
    hunger: float = 0.0
    thirst: float = 0.0
    fatigue: float = 0.0
    bladder: float = 0.0

    @property
    def pressure(self) -> float:
        return max(self.hunger, self.thirst, self.fatigue, self.bladder)


@dataclass
class RelationshipSnapshot:
    label: str = "stranger"              # "stranger", "friend", "crush", "partner", ...
    level: int = 0                       # 0–7 (your existing scheme)
    trust: float = 0.2                   # 0.0–1.0
    safety: float = 0.2                  # 0.0–1.0 (emotional safety)
    attachment: float = 0.0              # 0.0–1.0 (how bonded she feels)


@dataclass
class MemorySnippet:
    text: str
    weight: float = 1.0                  # relevance / emotional weight
    kind: str = "recent"                 # "recent", "episodic", "continuity"


@dataclass
class IntentContext:
    """
    Everything Nova's brain knows at the moment before speaking.
    This is passed INTO the IntentBuilder from higher-level engines.
    """
    user_message: str

    # Brain snapshots
    emotion: EmotionSnapshot = field(default_factory=EmotionSnapshot)
    mood: MoodSnapshot = field(default_factory=MoodSnapshot)
    needs: NeedsSnapshot = field(default_factory=NeedsSnapshot)
    relationship: RelationshipSnapshot = field(default_factory=RelationshipSnapshot)

    maturity: float = 0.5                 # 0.0–1.0 from maturity_engine
    persona_brief: str = ""               # short description from persona_engine

    # Memory
    recent_memory: List[MemorySnippet] = field(default_factory=list)
    episodic_memory: List[MemorySnippet] = field(default_factory=list)

    # Config flags
    allow_nsfw: bool = False              # your outer config; this module stays safe
    is_direct_question: bool = True       # parsed by dialogue manager
    question_type: str = "generic"        # "how_are_you", "what_if", "preference", etc.
    
    # Affection / relationship framing
    affection: float
    arousal: float
    comfort: float
    fluster: float
    nsfw_readiness: float


# ---------- intent object going TO the LLM ----------

@dataclass
class Intent:
    """
    High-level plan for what Nova is about to say.
    The LLM layer will translate this into natural language.
    """
    # Emotional state to communicate
    emotion_label: str
    fusion_label: Optional[str]
    mood_label: str
    maturity: float

    # Social / relationship framing
    relationship_label: str
    openness: float           # 0–1: how open/expressive to be
    vulnerability: float      # 0–1: how much of inner feelings to share
    playfulness: float        # 0–1: how playful vs serious
    hesitation: float = 0.0   # 0–1 level of pause/uncertainty

    # Conversation mode
    speaking_mode: str        # "answer", "answer_and_ask", "reflective", "light", "avoid", ...
    tone_style: str           # "soft", "calm", "pouty", "teasing", "flat", ...
    content_goal: str         # short text description of the goal of this utterance

    # Memory hook for the LLM to optionally mention
    memory_hint: Optional[str] = None

    # Flags
    mention_feeling_explicitly: bool = True
    mention_needs_subtly: bool = False
    ask_back: bool = False               # whether she should ask the user something


# ---------- main builder ----------

class IntentBuilder:
    """
    The brain of Nova's mouth.
    Takes internal state and decides *what* she intends to say,
    not the exact words.
    """

    def build_intent(self, ctx: IntentContext) -> Intent:
        # 1) Compute key traits
        openness = self._calc_openness(ctx)
        vulnerability = self._calc_vulnerability(ctx, openness)
        playfulness = self._calc_playfulness(ctx)

        # 2) Tone
        tone_style = self._decide_tone_style(ctx, openness, vulnerability)

        # 3) Speaking mode
        speaking_mode, content_goal, ask_back = self._decide_speaking_mode(
            ctx, openness, vulnerability
        )

        # 4) Memory hint
        memory_hint = self._pick_memory_hint(ctx, vulnerability)

        # 5) Emotion phrasing
        mention_feeling = True
        if ctx.question_type not in ("how_are_you", "emotional_check"):
            mention_feeling = vulnerability > 0.4 and ctx.emotion.intensity > 0.2

        # 6) Needs subtle mention
        mention_needs = ctx.needs.pressure > 0.5 and vulnerability > 0.3

        # 7) INITIAL NSFW readiness flag (pre-calculated)
        nsfw_ready = ctx.nsfw_readiness > 0.5

        # ---------- CREATE intent object ----------
        intent = Intent(
            emotion_label=ctx.emotion.primary or "neutral",
            fusion_label=ctx.emotion.fusion,
            mood_label=ctx.mood.label,
            maturity=ctx.maturity,
            relationship_label=ctx.relationship.label,
            openness=openness,
            vulnerability=vulnerability,
            playfulness=playfulness,
            speaking_mode=speaking_mode,
            tone_style=tone_style,
            content_goal=content_goal,
            memory_hint=memory_hint,
            mention_feeling_explicitly=mention_feeling,
            mention_needs_subtly=mention_needs,
            nsfw_ready=nsfw_ready,
            ask_back=ask_back,
        )

        # ---------- Emotional shaping ----------
        if ctx.nsfw_readiness > 0.6:
            intent.vulnerability += 0.1
            intent.playfulness += 0.1

        if ctx.fluster > 0.5:
            intent.hesitation += 0.15
            
        if intent.nsfw_ready:
            # slightly warmer tone
            intent.vulnerability += 0.05
            intent.playfulness += 0.05

            # but never force explicit — only changes tone
            if intent.speaking_mode == "answer":
                intent.speaking_mode = "soft"

        # ---------- Final NSFW readiness override ----------
        intent.nsfw_ready = ctx.nsfw_readiness > 0.5

        return intent

    # ---------- internal calculations ----------

    def _calc_openness(self, ctx: IntentContext) -> float:
        """How open/expressive she feels like being."""
        # Base from relationship trust & safety
        base = (ctx.relationship.trust * 0.5) + (ctx.relationship.safety * 0.3)
        # More attachment = more openness
        base += ctx.relationship.attachment * 0.2

        # Maturity: very low maturity can cause either oversharing or clamming up.
        if ctx.maturity < 0.3:
            base += 0.05  # slight overshare tendency with close relationships
        elif ctx.maturity > 0.7:
            base += 0.1   # high maturity = comfortable honesty

        # Very negative moods may reduce openness unless trust is high
        if ctx.mood.valence < 0.3 and ctx.relationship.trust < 0.5:
            base -= 0.2

        # Intense emotion makes her want to express something
        base += ctx.emotion.intensity * 0.15

        # Needs pressure reduces openness (tired, hungry, etc.)
        base -= ctx.needs.pressure * 0.15

        return clamp(base)

    def _calc_vulnerability(self, ctx: IntentContext, openness: float) -> float:
        """How much of her *inner* feelings she is willing to show."""
        v = openness

        # Strong negative fusion (e.g., "insecure", "ashamed") may *lower* vulnerability.
        if ctx.emotion.fusion in ("insecure", "ashamed", "guilty"):
            v -= 0.2

        # Warm / affectionate moods increase vulnerability with close partners.
        if ctx.mood.label in ("warm", "soft", "affectionate"):
            v += ctx.relationship.attachment * 0.3

        # High maturity means she can share feelings in a balanced way.
        v += (ctx.maturity - 0.5) * 0.3

        # Intense hurt but low trust → she hides more.
        if ctx.emotion.primary in ("hurt", "sad") and ctx.relationship.trust < 0.4:
            v -= 0.25

        # Clamp
        return clamp(v)

    def _calc_playfulness(self, ctx: IntentContext) -> float:
        """How playful/teasing vs serious the answer should feel."""
        p = 0.0

        # Positive valence + decent energy → more playful
        p += ctx.mood.valence * 0.4
        p += ctx.mood.energy * 0.3

        # Higher attachment encourages soft teasing
        p += ctx.relationship.attachment * 0.2

        # Very intense negative emotion kills playfulness
        if ctx.emotion.intensity > 0.6 and ctx.mood.valence < 0.4:
            p -= 0.4

        return clamp(p)

    def _decide_tone_style(self, ctx: IntentContext, openness: float, vulnerability: float) -> str:
        """Choose a high-level tone label."""
        # Baseline: calm, kuudere
        tone = "calm"

        if ctx.emotion.primary in ("sad", "hurt"):
            tone = "soft"
        if ctx.emotion.primary in ("anxious", "nervous"):
            tone = "hesitant"
        if ctx.emotion.primary in ("annoyed", "frustrated"):
            tone = "flat"

        # Pouting logic (her key reaction)
        if ctx.emotion.fusion in ("insecure", "jealous") or ctx.emotion.primary in ("hurt", "annoyed"):
            if ctx.maturity < 0.6 and ctx.relationship.trust > 0.4:
                tone = "pouty"

        # Warm affection
        if ctx.mood.label in ("warm", "soft", "affectionate") and ctx.relationship.attachment > 0.4:
            tone = "gentle"

        # High playfulness can soften tone
        if self._calc_playfulness(ctx) > 0.6:
            if tone not in ("pouty", "flat"):
                tone = "light"

        return tone

    def _decide_speaking_mode(
        self,
        ctx: IntentContext,
        openness: float,
        vulnerability: float,
    ) -> tuple[str, str, bool]:
        """
        Decide whether Nova just answers, answers and asks back,
        becomes reflective, etc.
        Returns: (mode, content_goal, ask_back)
        """
        ask_back = False

        # Default content goal
        content_goal = "answer the user's message naturally"

        if ctx.question_type in ("how_are_you", "emotional_check"):
            mode = "answer"
            content_goal = "briefly describe her current state"

            # If openness is decent and relationship is not cold, ask back.
            if openness > 0.4 and ctx.relationship.trust > 0.3:
                ask_back = True
                mode = "answer_and_ask"
                content_goal = "describe state and gently ask how the user is"

        elif ctx.question_type == "what_if":
            mode = "reflective"
            content_goal = "imagine what she would feel and do in that scenario, based on her personality and history"

        elif ctx.question_type == "preference":
            mode = "answer"
            content_goal = "state her preference honestly, with a bit of explanation"

        else:
            # Generic question / statement
            mode = "answer"
            if openness > 0.5 and ctx.emotion.intensity > 0.3:
                mode = "answer_and_ask"
                ask_back = True
                content_goal = "answer and show curiosity about the user's side"

        # If vulnerability is very low, avoid deep topics.
        if vulnerability < 0.2:
            if mode == "reflective":
                mode = "light"
                content_goal = "give a simple, surface-level response without going deep"

        return mode, content_goal, ask_back

    def _pick_memory_hint(self, ctx: IntentContext, vulnerability: float) -> Optional[str]:
        """
        Optionally select a single memory line to color her answer.
        Only used when vulnerability is reasonably high.
        """
        if vulnerability < 0.4:
            return None

        # Prefer recent emotionally-weighted memories
        pool: List[MemorySnippet] = sorted(
            ctx.recent_memory + ctx.episodic_memory,
            key=lambda m: m.weight,
            reverse=True,
        )

        if not pool:
            return None

        top = pool[0]
        # Keep it short – IntentBuilder never sends long text.
        return top.text[:200]

