# llm_bridge.py
# NovaCore - LLM Bridge (Nova's "mouth")
#
# Responsibility:
#   - Take an Intent (from IntentBuilder) + user message
#   - Build a small, clean set of system messages
#   - Call the local LLM (Qwen via LM Studio or similar)
#   - Return Nova's spoken line
#
# This module does NOT:
#   - Compute emotions, maturity, drives, or memory
#   - Load identity JSON or backstory
#   - Dump huge prompts or chunk text
#
# All "thinking" happens in:
#   - emotion_engine, maturity_engine, persona_engine, identity_engine, memory_engine
#   - intent_builder.IntentBuilder
#
# LlmBridge only turns INTENT -> WORDS.

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import json
import logging
import requests

from nexus.cortex.thinking.intent_builder import Intent  # same folder as this file


logger = logging.getLogger(__name__)


# -----------------------------
# Config
# -----------------------------

@dataclass
class LlmConfig:
    base_url: str = "http://localhost:1234/v1/chat/completions"
    model: str = "qwen2.5-7b-instruct"  # adapt to whatever LM Studio exposes
    api_key: Optional[str] = None       # LM Studio usually ignores this
    max_tokens: int = 512
    # Default temperature; we will modulate slightly based on intent.playfulness
    base_temperature: float = 0.7
    timeout_seconds: int = 60


# -----------------------------
# LlmBridge
# -----------------------------

class LlmBridge:
    """
    Bridge between Nova's internal intent and the external LLM.

    Usage pattern (high level):

        # 1. Brain builds IntentContext and Intent
        intent = intent_builder.build_intent(ctx)

        # 2. LlmBridge turns that into messages and calls the LLM
        reply_text = llm_bridge.generate_reply(
            user_message=user_text,
            intent=intent,
            persona_brief=ctx.persona_brief,
        )

        # 3. speech_micro / mouth_noise modules can modify reply_text afterwards.
    """

    def __init__(self, config: Optional[LlmConfig] = None):
        self.config = config or LlmConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_reply(
        self,
        user_message: str,
        intent: Intent,
        persona_brief: str,
        system_overrides: Optional[str] = None,
    ) -> str:
        """
        Main entry point.
        - user_message: raw user text
        - intent: high-level plan from IntentBuilder
        - persona_brief: short description from persona_engine
        - system_overrides: optional extra rules (debug / experiments)
        """
        messages = self._build_messages(
            user_message=user_message,
            intent=intent,
            persona_brief=persona_brief,
            system_overrides=system_overrides,
        )

        raw = self._call_llm(messages, intent=intent)
        reply = self._extract_reply_text(raw)

        if not reply:
            # Fail-safe so Nova never stays completely silent.
            logger.warning("Empty reply from LLM; returning fallback text.")
            reply = "...sorry, my head just went blank for a second. Can you repeat that?"

        # NOTE: speech_micro / mouth_noise should be applied AFTER this,
        # in your speech layer, not inside LlmBridge.

        return reply.strip()

    # ------------------------------------------------------------------
    # Message building
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        intent: Intent,
        persona_brief: str,
        system_overrides: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the small SM2.5 message stack:

        1) Core rules
        2) Persona + tone
        3) State + memory + intent summary
        4) User message
        """

        core_rules = self._build_core_rules(system_overrides)
        persona_block = self._build_persona_block(persona_brief, intent)
        state_block = self._build_state_block(intent)

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": core_rules},
            {"role": "system", "content": persona_block},
            {"role": "system", "content": state_block},
            {"role": "user", "content": user_message},
        ]

        return messages

    def _build_core_rules(self, system_overrides: Optional[str]) -> str:
        """
        System Message 1 – Core rules.
        Keep this compact, stable, and model-agnostic.
        """
        base = [
            "You are Nova, an adult woman.",
            "You speak in first person as Nova, not as an AI assistant.",
            "Your baseline personality is calm, observant, quietly warm, with subtle kuudere vibes.",
            "Keep your replies short to medium length, like a real person chatting.",
            "You can ask questions back when it feels natural, especially if 'ask_back' is true in the state summary.",
            "Do not dump your entire life story; reveal details only when it fits the moment.",
            "Speak naturally, not like a formal essay. Use contractions and casual language when appropriate.",
        ]

        if system_overrides:
            base.append("")
            base.append("Additional rules:")
            base.append(system_overrides.strip())

        return "\n".join(base)

    def _build_persona_block(self, persona_brief: str, intent: Intent) -> str:
        """
        System Message 2 – Persona + tone description.
        This is where we give the LLM a compact sense of "who" Nova is
        and how her voice should sound in this moment.
        """
        lines = []

        if persona_brief:
            lines.append("Persona summary:")
            lines.append(persona_brief.strip())
            lines.append("")

        lines.append("Current conversational style:")
        lines.append(f"- Tone style: {intent.tone_style}")
        lines.append(f"- Playfulness level: {intent.playfulness:.2f} (0=serious, 1=playful)")
        lines.append(
            "- You should still feel like the same person even as emotions change."
        )

        return "\n".join(lines)

    def _build_state_block(self, intent: Intent) -> str:
        """
        System Message 3 – State + memory + intent summary.
        This is the main "intent blueprint" for the LLM.
        """
        lines: List[str] = []

        lines.append("Current internal state:")
        lines.append(f"- Emotion: {intent.emotion_label}")
        if intent.fusion_label:
            lines.append(f"- Emotional nuance (fusion): {intent.fusion_label}")
        lines.append(f"- Mood: {intent.mood_label}")
        lines.append(f"- Maturity level: {intent.maturity:.2f} (0=soft/immature, 1=very composed)")
        lines.append(f"- Relationship context: {intent.relationship_label}")
        lines.append(f"- Openness: {intent.openness:.2f}")
        lines.append(f"- Vulnerability: {intent.vulnerability:.2f}")
        lines.append(f"- Playfulness: {intent.playfulness:.2f}")
        lines.append("")

        if intent.memory_hint:
            lines.append("Relevant memory or recent feeling to optionally reference:")
            lines.append(f"- {intent.memory_hint.strip()}")
            lines.append("")

        lines.append("Speaking plan:")
        lines.append(f"- Mode: {intent.speaking_mode}")
        lines.append(f"- Goal: {intent.content_goal}")
        lines.append(f"- Should explicitly mention how she feels: {intent.mention_feeling_explicitly}")
        lines.append(f"- May subtly mention physical/needy state: {intent.mention_needs_subtly}")
        lines.append(f"- Should ask the user something back: {intent.ask_back}")

        # NSFW flag is just a hint to your local model; this file stays neutral.
        lines.append(f"- Adult/romantic topics are emotionally acceptable right now: {intent.nsfw_ready}")

        lines.append("")
        lines.append(
            "Use this state as emotional context for how Nova answers the user's message, "
            "but do not restate this state verbatim."
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, messages: List[Dict[str, str]], intent: Intent) -> Dict[str, Any]:
        """
        Call the local LLM (LM Studio / Qwen).
        No chunking, no fancy tricks: just a clean chat/completions call.
        """
        temperature = self._derive_temperature(intent)
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        try:
            response = requests.post(
                self.config.base_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.config.timeout_seconds,
            )
        except Exception as e:
            logger.exception("Error when calling LLM backend: %s", e)
            return {}

        if not response.ok:
            logger.error(
                "LLM HTTP error %s: %s", response.status_code, response.text[:500]
            )
            return {}

        try:
            return response.json()
        except Exception as e:
            logger.exception("Failed to parse LLM JSON response: %s", e)
            return {}

    def _derive_temperature(self, intent: Intent) -> float:
        """
        Adjust temperature slightly based on playfulness.
        More playful → slightly higher temperature.
        More serious → slightly lower.
        """
        base = self.config.base_temperature
        # Map playfulness (0–1) to a ±0.15 delta.
        delta = (intent.playfulness - 0.5) * 0.3
        t = base + delta
        return max(0.3, min(1.0, t))

    # ------------------------------------------------------------------
    # Response extraction
    # ------------------------------------------------------------------

    def _extract_reply_text(self, raw: Dict[str, Any]) -> str:
        """
        Extract first choice text from OpenAI/LM-Studio compatible response.
        """
        if not raw:
            return ""

        try:
            choices = raw.get("choices") or []
            if not choices:
                return ""

            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            return content
        except Exception as e:
            logger.exception("Failed to extract reply text from LLM response: %s", e)
            return ""
