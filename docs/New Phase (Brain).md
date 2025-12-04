Alright, brain only. No games, no VR, just her mind from “messy” → “finished.”

Here’s a full brain roadmap, from now until we can honestly say:

“Nova’s brain works; everything else is layers on top.”

0. **What “Brain Complete” means**

Nova’s brain is done when:

All thinking runs through BrainLoop (no bypasses in nova.py).

Every user message goes through a single router and hits:

Needs/Body

Memory + Privacy

Continuity

Intent

Emotion/Mood/Fusion

LLM (LlmBridge)

She has:

stable mood and emotions,

believable needs/body state,

working short- and long-term memory,

identity/relationship awareness,

small, clean context to the LLM.

There’s a simple diagnostic mode to prove it works.

Everything below is just how we get there.

1. **Core Entry & BrainLoop Wiring**

Goal: nova.py doesn’t “think” itself — it delegates to the brain.

Tasks:

In nova.py:

Create a clean loop:

read user text

call brain_loop.process_turn(user_text)

speak the reply, repeat.

Remove the direct calls like memory.on_user_message(...), continuity.on_user_message(...).

In BrainLoop:

Ensure process_turn():

receives user_text

creates / updates a shared nova_state

calls the UserEventRouter

calls LlmBridge

returns final reply text.

Exit condition:
Every conversation turn passes through BrainLoop.process_turn, and nova.py is just I/O glue.

2. **UserEventRouter & Intent Integration**

Goal: One unified path for each user message.

Tasks:

In UserEventRouter (or equivalent):

on_user_message(text, state) should:

call MemoryEngine.on_user_message

call ContinuityEngine.on_user_message

call IntentBuilder.build_intent

notify Idle/Life/Needs if needed.

In IntentBuilder:

Standardize output shape:

Intent {
    tone,
    emotion_hint,
    topic_shift,
    nsfw_ready,
    playfulness,
    priority,
    ...
}


Attach this Intent to nova_state so LlmBridge can see it.

Make sure LlmBridge uses:

intent.tone

intent.emotion_hint

other flags to shape style, not to rewrite identity.

Exit condition:
One function (router.on_user_message) fans out to all modules, and we can print/log the built Intent per turn.

3. **Needs / Body Simulation Online**

Goal: NeedsEngine actually runs and affects state every turn.

Tasks:

In BrainLoop.process_turn:

Call needs_engine.update(state, time_now) each turn.

Let NeedsEngine change:

fatigue

bladder

hunger

focus

etc.

In nova_state:

Add a compact summary function for LLM:

build_llm_state_summary()  # mood + 2–3 need facts


In any delay logic:

Base pauses / “I was away” messages on NeedsEngine thresholds, not randomness.

Exit condition:
You can see needs values change over turns, and they affect mood / timing / small explanations.

4. **Memory & Privacy (Modern Path Only)**

Goal: Use the new MemoryEngine + PrivacyGuard, no legacy APIs.

Tasks:

In BrainLoop / router:

On user message:

pass text through PrivacyGuard (if marked sensitive, treat accordingly)

store event in MemoryEngine (short-term).

On “sleep” / shutdown / long idle:

Call MemoryConsolidationEngine.run_sleep_cycle (or equivalent) to:

consolidate short-term into episodic memories,

decay / compress old ones,

produce a brief summary if needed.

In continuity/time expectations (TEE):

Connect MemoryEngine/Continuity so:

plans and promises are remembered with timestamps,

“you said we’d do X later” is possible.

Remove or adapt any old get_latest_session_summary/save_session_summary calls in nova.py to use the new engine or compatibility wrappers.

Exit condition:
Memories are written and consolidated only via the new engines, and there are no calls to deprecated memory methods in the live loop.

5. **Identity, Persona & Relationship Context**

Goal: Nova knows who she is and who you are — without flooding prompts.

Tasks:

Identity split (minimum viable):

Ensure identity is split across multiple JSONs / structures:

identity/core

personality

relationship_state

maybe romance / nostalgia / trauma as separate slices, even if simple.

Identity access layer:

Implement a small helper like:

identity.get_core_line()
identity.get_relationship_line(user_id)
identity.get_arc_line()


Keep each line short (1–2 sentences).

PersonaEngine:

Return a brief persona string (a few sentences max).

Never dump a full essay to LLM.

Context builder (for LlmBridge):

Build:

core behavior rules

brief persona

one relationship line

1–2 lines of recent-memory summary

1 short state summary (mood/needs)

No full childhood/romance dumps unless the user directly asks.

Exit condition:
System prompt is always small and predictable; identity/relationship data is pulled through one narrow, controlled path.

6. **Emotion, Mood, Fusion → Output**

Goal: Emotional engines actually shape how she speaks, not just internal floats.

Tasks:

In emotional state model:

Ensure current mood, primary emotion, intensity are accessible as clean values (or tags).

In nova_state.build_llm_state_summary():

Inject 1–2 small hints:

e.g. “Nova is slightly tired but calm.”

“Nova feels a bit hurt but trying to stay composed.”

In LlmBridge:

Use mood/emotion + intent to:

pick adverbs / rhythm,

slightly alter formality or warmth,

control pouting / teasing frequency (within your spec).

Make sure no engine contradicts another:

Fusion engine decides final “tone preset”

LlmBridge uses that preset instead of inventing its own.

Exit condition:
When you adjust emotions/mood manually (or via events), her wording clearly shifts in consistent, grounded ways.

7. **Diagnostics & Brain Self-Check**

Goal: Verify all layers work without guessing.

Tasks:

Add a debug / test mode:

e.g. nova.py --diagnostics

Runs through a fixed script:

neutral greeting

emotional event

promise/plan

long idle / sleep

follow-up question

Log for each step:

Needs state

Emotion + mood

Memory writes & consolidation

Continuity expectations

Intent output

LLM prompt length & structure (sanity check)

Simple pass/fail checks:

Did NeedsEngine values change as expected?

Did MemoryConsolidation run?

Did continuity store/retrieve the plan?

Did context stay under the target size?

Exit condition:
You can run one command, look at logs, and know if the brain is behaving without manually probing everything.

8. **“Brain Done” Checklist**

Before you move on to games or VR, you should be able to say yes to:

 nova.py delegates all thinking to BrainLoop.

 Every user message runs through UserEventRouter.

 NeedsEngine updates every turn and visibly affects behavior.

 Memory uses the new engine + PrivacyGuard path only.

 Continuity/TEE tracks promises and time expectations.

 Identity/persona/relationship are split and accessed via a tiny, stable API.

 LlmBridge always sends a small, well-structured prompt.

 Emotion/mood/fusion actually shape the reply style.

 A diagnostic mode exists and passes.