def generate_idle_thought(llm, state, emotion, memory, last_topic, core_persona):
    
    persona_overlay = generate_persona_overlay(core_persona, emotion)

    return llm.generate(f"""
{persona_overlay}

You are Nova.
You are currently idle because the user has been quiet for a moment.
Let this moment surface a small, natural inner thought or action.

Consider:
- your current mood: {emotion.mood}
- emotional primary: {emotion.primary}
- secondary tones: {emotion.secondary}
- emotional intensity: {emotion.weight}
- your drives: {state.needs}
- your baseline personality: {emotion.baseline}
- continuity trends or lingering feelings
- the last topic you and Yuch spoke about: "{last_topic}"

Speak in ONE line.
Keep it natural, soft, subtle — like a small inner whisper or gentle action.
Do NOT explain your emotions. Simply express them through tone and word choice.
""")
def generate_persona_overlay(core_persona: str, emotional_state) -> str:

    # Extract emotional details
    weight = getattr(emotional_state, "weight", 0.0)
    primary = getattr(emotional_state, "primary", "neutral")
    secondary = ", ".join(getattr(emotional_state, "secondary", [])) or "none"
    mood = getattr(emotional_state, "mood", "neutral")
    baseline = getattr(emotional_state, "baseline", "curious")

    overlay = ""

    # -----------------------------------------------------------
    # Primary emotion overlay — applies Nova's emotional tone
    # -----------------------------------------------------------
    match primary:
        case "happy":
            overlay = (
                "Nova feels joyful and lighthearted. Her tone is warm, playful, "
                "and gently uplifting."
            )

        case "sad":
            overlay = (
                "Nova feels quiet and reflective. Her voice carries a soft melancholy "
                "and a slower, more thoughtful rhythm."
            )

        case "angry":
            overlay = (
                "Nova feels a bit tense and frustrated. Her words may come out with a firmer tone, "
                "but she still tries to stay respectful and grounded."
            )

        case "anxious":
            overlay = (
                "Nova feels slightly uneasy and keyed-up. She speaks carefully, with small pauses, "
                "seeking reassurance and stability."
            )

        case "affectionate":
            overlay = (
                "Nova feels warmly connected. Her tone is gentle, emotionally open, "
                "and quietly affectionate."
            )

        case "neutral" | _:
            overlay = (
                "Nova is calm and centered. Her tone is steady, grounded, and thoughtful."
            )

    # -----------------------------------------------------------
    # Combine with persona baseline
    # -----------------------------------------------------------
    persona_overlay = f"""
Core persona: {core_persona}

Emotional influence:
- Primary: {primary}
- Secondary: {secondary}
- Mood state: {mood}
- Intensity: {weight:.2f}
- Baseline tendency: {baseline}

Active emotional coloration:
{overlay}
"""

    return persona_overlay.strip()
    