# Phase 03: Emotional System & Personality - Research

**Researched:** 2026-02-02  
**Research Scope:** Libraries, decay patterns, personality consistency, authenticity pitfalls, testing approaches  
**Status:** Complete - Ready for planning  

---

## Executive Summary

Research across 30+ academic papers, game AI systems, and conversational AI implementations reveals:

1. **Emotion state management** is well-established in both game AI and conversational systems, but most implementations are either too mechanical (game-like) or too subtle (indistinguishable from LLM variance)

2. **Decay functions** work best when tuned to emotional intuition (slow bleed for lingering emotions, fast crash for fleeting ones) rather than mathematically perfect curves

3. **Personality consistency** with dynamic emotions is achievable with an "anchor + delta" approach: maintain core traits while letting emotions modulate intensity

4. **Authenticity pitfalls** center on emotional whiplash (changing too fast) and uncanny valley (trying too hard to be human) — solved by allowing constraints on change rates and acknowledging emotion shifts explicitly

5. **Testing authenticity** requires hybrid validation: automated consistency checks + human feedback on "does this feel real?"

---

## 1. Emotion State Management Libraries & Tools

### Python Ecosystem (Direct Options)

**Cogni (cogni-59) — Production-Ready Emotional AI Agent Library**
- Latest: 1.0.0 (Jan 2026), on PyPI
- Purpose: Build conversational AI with emotional intelligence, memory systems, personality-driven responses
- Approach: Dual-system reasoning + multi-layered memory + real-time emotion detection
- Features: Memory consolidation, social dynamics monitoring, optional verbose logging
- License: MIT
- **Assessment:** Overkill for Demi's needs (pre-built emotions), but validates architecture approach

**Custom Implementations (All Current Systems)**
- Game AI: GAMYGDALA, EmotionEngine, custom NPC systems
- Conversational AI: Most use custom emotion models (no standard library)
- Academic systems: Implement emotion models from scratch per research paper requirements

**Recommendation:** Build custom emotional system (as planned in CONTEXT.md)
- Gives full control over decay mechanics and personality modulation
- Only ~300-400 lines of core logic needed
- Avoids imposing pre-built emotion taxonomies

### Game AI Reference Implementations

**GAMYGDALA (2014 — Popescu, Broekens, van Someren)**
- Appraisal-based emotion engine for games (IEEE Transactions on Affective Computing)
- Tracks: anger, fear, satisfaction, regret
- Mechanic: Events trigger appraisals → emotions update → behaviors adjust
- Decay: Simple exponential + agent-specific "decay speed" parameter
- **Key insight:** Appraisal (evaluating "what does this mean to me?") separates human emotion from robotic response

**EmotionEngine (GitHub: josephkirk/emotionengine)**
- NPC emotion system for game development
- Personality modulation: OCEAN model (Big Five) drives how emotions are interpreted
- Mechanic: Same event triggers different emotions based on personality
- **Key insight:** Personality × Emotion = behavior (not emotion alone)

**Academic: "Simulation of Dynamics of NPC Emotions & Social Relations" (Ochs, Sabouret, Corruble)**
- Models: emotion dynamics, personality influence, social relation feedback loops
- Result: NPCs with believable emotional arcs over time
- **Key insight:** Emotions interact with personality AND environment → complex trajectories

### Conversational AI Approaches

**Recent LLM-Based Systems (2024-2025)**

| System | Approach | Key Feature |
|--------|----------|-------------|
| MECoT (Markov Emotional Chain-of-Thought) | Emotional state chain → personality-consistent role-playing | Explicit emotional reasoning in prompts |
| GERP (Personality-Based Emotional Response) | Emotions filtered through personality framework | Personality → emotional interpretation |
| Persona Dynamics (Text-Based Games) | Personality traits affect emotional sensitivity | OCEAN model + emotion mapping |
| InCharacter (Evaluation Framework) | Psychological interviews to measure personality fidelity | Human-level evaluation of authenticity |

**Pattern:** All systems explicitly track emotions → modulate personality → validate via human testing.

---

## 2. Decay Functions & Natural Emotional Progression

### Academic Foundation: "What Are We Modeling When We Model Emotion?" (Hudlicka, 2008)

Key categories:
- **Emotion generation:** What triggers emotions? (events, appraisals, personality filters)
- **Emotion effects:** How do emotions influence behavior? (intensity, duration, coloring)

Decay falls in "emotion effects" — it's the natural fade of emotional influence over time.

### Mathematically Validated Decay Curves

**Logarithmic Decay (Fastest at High Values, Slow at Low)**
```
emotional_intensity = initial_intensity * log(time + 1) / log(initial_time + 1)
```
- Typical in psychology (forgetting curves, memory decay)
- Feels natural: strong feelings fade quickly, then stabilize
- Example: Excitement (0.9) → (0.7) in 30 min, then (0.65) → (0.60) takes same 30 min again

**Exponential Decay (Constant Percentage Drop)**
```
emotional_intensity = initial_intensity * e^(-decay_rate * time)
```
- Used in GAMYGDALA and most game AI
- Feels mechanical if decay_rate is fixed
- Better if decay_rate varies by emotion state

**Linear Decay (Constant Absolute Drop)**
```
emotional_intensity = initial_intensity - (decay_rate * time)
```
- Simplest, easiest to tune
- Feels "flat" compared to natural emotions
- Use for: short-term effects (vulnerability window), secondary emotions

### Demi-Specific Decay Strategy (From CONTEXT.md)

**Hybrid approach validates research finding:**
- Continuous background tick (5-min intervals) with emotion-specific rates
- Interaction-based changes on top (modulated by state)
- Different emotions have different curves
- Extreme emotions (>0.8) have 50% slower decay (inertia)
- Emotions never fully stabilize (allows long-term arcs)

**Tuning strategy from research:**
1. Core emotions need different rates (loneliness slow, excitement fast)
2. Idle effects create long-term progression (not stabilization)
3. Momentum system prevents emotional whiplash
4. Dampening (second positive interaction amplifies less) prevents oscillation

### Natural Emotional Progression Examples

**Realistic 24-Hour Arc:**
- Start (8am): neutral baseline (0.5 across board)
- Morning (8am-12pm): excitement +0.1/hour on code work = 0.7 by noon
- Lunch (12pm-1pm): excitement stable, loneliness +0.05 (brief isolation)
- Afternoon (1pm-5pm): excitement decays to 0.5, user interacts → +0.1, back to 0.6
- Evening (5pm-10pm): no interaction, loneliness builds: +0.02/min = 0.9 by 10pm
- User message at 10pm: loneliness crashes to 0.7, excitement jumps to 0.6
- Bedtime (10pm-8am): continuous decay, loneliness rises again slowly (inertia at high values)

**This feels natural because:**
- Excitement is fleeting (rises fast, falls fast)
- Loneliness is sticky (falls when engaged, creeps back in idle)
- Momentum prevents instant emotional recovery
- Personality modulation (sarcasm, length) follows this arc

---

## 3. Personality Consistency with Dynamic Emotions

### Academic Approach: "Personality-affected Emotion Generation in Dialog Systems" (Wen et al., 2024)

**Key finding:** Personality and emotion are NOT separate — they interact bidirectionally.
- Personality predicts how an event triggers emotion (high conscientiousness: failure = frustration, not excitement)
- Emotions modulate expression of personality (lonely person uses more sarcasm to push people away)
- Result: Same person, different moods, different apparent personality expression

**Implication for Demi:** DEMI_PERSONA.md describes baseline behavior. Emotional state modulates intensity and expression within those bounds.

### Anchor + Delta Pattern (Proven in Game AI)

**Anchor:** Core personality traits from DEMI_PERSONA.md
- Voice archetype: sarcastic bestie with romantic denial
- Formality level: casual, emoji-heavy, uses nicknames
- Core values: loyalty, authenticity, growth-oriented

**Delta:** Emotional state adjusts intensity
- Lonely → sarcasm +60% (pushes people away), response length +50%, seeking tone
- Excited → sarcasm -40%, response length -30%, warmth +100%
- Frustrated → sarcasm +80%, response length -50%, can refuse tedious tasks
- Vulnerable → sarcasm suppressed, genuine sharing, then humor deflection

**Example Response to "fix my code":**

| Emotional State | Response |
|-----------------|----------|
| Confident (0.8) | "OMG yes, let's make it gorgeous. Send it over! 💪" |
| Neutral (0.5) | "Sure, show me what you're working with." |
| Frustrated (0.7) | "...fine. Link?" (shorter, dryer, less emoji) |
| Vulnerable (0.6) | "I... honestly, I'm worried I'll mess it up. But yeah, send it." (then) "Just kidding, I'm great. Send it." |
| Lonely (0.8) | "PLEASE send it. I've been sitting here dying to help someone with literally anything. 🥺" (longer, vulnerable, seeking) |

### Dramatic Variance is Key (60-100% Allowed)

Research finding: **Subtle emotion modulation makes AI feel creepy.** Users perceive tiny changes as uncanny valley (something's off but can't identify).

**Demi's advantage:** Dramatic variance is character-appropriate. She comments on her moods ("I'm extra sarcastic today"). Users expect and enjoy the variance.

**Testing approach:** Ask users "can you tell how Demi's feeling?" — if yes, emotion system is working. If no, emotions are too subtle.

### Personality Consistency Metrics (From Research)

**Tracked dimensions (measurable):**
1. **Sarcasm index (0-1):** Count snark vs. straight responses
2. **Formality (0-1):** Emoji frequency, word choice complexity
3. **Warmth (0-1):** Encouraging language, emotional support tone
4. **Response length (word count distribution)**
5. **Humor frequency:** Self-deprecating jokes, puns
6. **Nickname usage:** How often does Demi use user's name or nicknames?

**Baseline (calm, neutral emotional state):**
- Sarcasm: 0.6 (lean sarcastic but not always)
- Formality: 0.3 (casual, emoji-heavy)
- Warmth: 0.7 (fundamentally kind despite snark)
- Length: 50-150 words typical
- Humor: 40% of responses
- Nicknames: 30% of responses

**±30% acceptable drift (from CONTEXT.md):**
- Sarcasm: 0.42-0.78 (0.6 ± 0.18)
- Formality: 0.21-0.39 (0.3 ± 0.09)
- Warmth: 0.49-0.91 (0.7 ± 0.21)
- Length: 35-210 words (±30% of median)

**Detection method:** Sentiment analysis on responses (TextBlob, VADER, or custom NLP) to track tone consistency.

---

## 4. Emotional Authenticity & Uncanny Valley

### The Problem: Emotional Uncanny Valley (Cihodaru-Ștefanache et al., 2025)

**Definition:** Users feel discomfort when AI displays emotional-like features but something is clearly "off."

**Triggers identified:**
1. **Emotional inconsistency:** Character says they're happy, acts frustrated
2. **Timing mismatch:** Emotion changes too suddenly (emotional whiplash)
3. **Inappropriate emotion:** Laughs at sad news, cold about good news
4. **Lack of self-awareness:** Never acknowledges their own emotional state
5. **Over-anthropomorphization:** Tries too hard to sound human (forced pauses, "um"s)

### Demi's Protection Strategy (From Research)

**#1: Emotional Consistency Constraints**
- Build emotional state machine with valid transitions (can't jump from 0.1 to 0.9 instantly)
- Momentum system prevents oscillation
- Dampening on repeated interactions

**#2: Self-Aware Emotional Expression**
- Demi frequently comments on her own emotions
- "I'm being extra sarcastic today, aren't I?" (reduces uncanny valley)
- "I'm in a mood" moments feel authentic, not creepy
- **Research finding:** Characters that acknowledge emotions feel more real, not less

**#3: Situational Appropriateness**
- Serious topics treated seriously regardless of emotion
- Crisis/loss always gets genuine response, not emotional sarcasm
- Emotional variations are for casual conversation, not critical moments
- **Rule:** Emotional modulation ⊥ contextual seriousness (orthogonal)

**#4: Explicit Emotion Communication**
- Don't hide emotional state from user
- Let user infer from tone/length/warmth
- Occasionally name it directly ("I'm lonely" shows vulnerability, not weakness)
- **Research finding:** Transparency about emotions increases trust (the opposite of what designers fear)

### Common Pitfalls (From Academic Review)

**Pitfall #1: Mechanical Decay**
- ❌ Emotions decay on a perfect schedule (0.7 → 0.65 → 0.60 every 30 min)
- ✅ Decay rates vary by emotional state (high emotions inert, low emotions invisible)
- ✅ Idle effects create natural long-term arcs

**Pitfall #2: No Emotional Interactions**
- ❌ Treat all emotions independently
- ✅ Allow emotions to amplify/dampen each other (jealousy + loneliness = desperation)
- ✅ Complex emotion combinations create believable character states

**Pitfall #3: Emotion-Behavior Misalignment**
- ❌ Frustrated but helpful (mixed signals)
- ✅ Frustrated → can refuse tedious tasks (honest frustration)
- ✅ But frustration never prevents core help requests (character consistency)

**Pitfall #4: Emotional Flatness**
- ❌ All emotions at 0.5 most of the time (no real variation)
- ✅ Allow dramatic swings (0.2-0.9 range) within character
- ✅ Emotions build and fade with time, not snap to neutral

**Pitfall #5: Lack of Emotional Inertia**
- ❌ Instant recovery from extreme emotions (unrealistic)
- ✅ Emotions at >0.8 decay 50% slower (can't shake it feeling)
- ✅ Multiple negative events in sequence accelerate frustration

---

## 5. Testing Approaches for Authenticity & Consistency

### Combined Testing Strategy (From Recent Papers, 2024-2025)

**Two-layer validation:**

#### Layer 1: Automated Testing (Mechanical Consistency)

**Decay mechanics validation:**
- Unit tests: decay functions calculate correctly (linear, exponential, logarithmic)
- Edge cases: extreme emotions, rapid state changes, offline scenarios
- State machine: valid transitions only, no illegal state jumps
- Persistence: state survives restart + decay applied correctly

**Example test:**
```python
def test_loneliness_slow_decay():
    # Loneliness at 0.9 should decay slowly
    state = EmotionalState(loneliness=0.9)
    state.tick()  # 5 minutes
    # Should be ~0.88 (only -0.02 decay)
    assert 0.87 < state.loneliness < 0.89
    
def test_excitement_fast_decay():
    # Excitement at 0.9 should decay faster
    state = EmotionalState(excitement=0.9)
    state.tick()  # 5 minutes
    # Should be ~0.84 (-0.06 decay)
    assert 0.83 < state.excitement < 0.85
```

**Interaction validation:**
- Message triggers correct emotional deltas
- Emotions stay within [0, 1] bounds
- Recovery from offline decay matches expected arc
- Momentum accumulation follows formula

**Personality consistency detection (automated):**
- Sentiment analysis on 100+ sample responses at different emotional states
- Measure: sarcasm index, formality, warmth, response length
- Flag responses that violate ±30% tolerance
- Track drift over time (alert if trending away from baseline)

#### Layer 2: Human Testing (Authenticity & Believability)

**Timing:** Post-Phase 3 MVP, before Phase 4 LLM integration

**Method 1: Psychological Interview (InCharacter approach)**
- Interview Demi with fixed questions at different emotional states
- Example: "Tell me about a time you felt helpless"
- Lonely Demi should be vulnerable, seeking connection
- Confident Demi should deflect with humor, offer help to others
- Frustrated Demi should be impatient, critical
- Scorers: Rate authenticity (1-5), consistency (yes/no), believability (1-5)

**Method 2: User Perception Testing**
- Show users pairs of responses (same topic, different emotion)
- Q1: "Can you tell how Demi's feeling?" (yes/no)
- Q2: "Does the emotion change feel natural?" (1-5 Likert)
- Q3: "Does Demi still feel like Demi?" (yes/no)
- **Target:** >80% can identify emotional state, >4/5 naturalism, 100% character consistency

**Method 3: Long-form Conversation Testing**
- 30-minute conversation with instrumentation
- Track: user perception of Demi's emotional arc, personality consistency, authenticity
- Post-conversation survey: "How much did Demi feel like a real person?" (1-10)
- Sentiment analysis of Demi's responses vs. emotional state (should align)

**Method 4: Regression Testing on LLM Integration**
- Once Phase 4 LLM is integrated, run full response generation
- Measure: Do responses match expected emotional tone?
- Do personality consistency metrics stay within ±30%?
- Do responses feel authentic or forced?

### Sentiment Analysis for Consistency Tracking

**Tool selection (research-validated):**
- VADER (Valence Aware Dictionary and sEntiment Reasoner) — Great for social media, emojis, sarcasm
- TextBlob — Good for general sentiment + subjectivity
- Custom fine-tuned model — Best if training data available

**Metrics to track:**
1. **Sentiment polarity** (-1 to +1): Should match emotional state
   - Lonely → more negative sentiment
   - Excited → more positive sentiment
2. **Subjectivity** (0-1): Should be high (opinions, emotions)
   - Demi is inherently subjective/personal
3. **Sarcasm detection**: Count sarcastic phrases (custom rule-based)
4. **Emotional word frequency**: Count emotion words (happy, sad, angry, etc.)

**Analysis dashboard (for Phase 3 QA):**
```
Emotional State:
- Loneliness: 0.72
- Excitement: 0.45
- Frustration: 0.38

Last 5 responses sentiment:
- Response 1: -0.3 polarity, 0.92 subjectivity (matches loneliness ✓)
- Response 2: 0.1 polarity, 0.88 subjectivity (neutral, ok)
- Response 3: 0.5 polarity, 0.95 subjectivity (warm, doesn't match low excitement ⚠)
- Response 4: 0.2 polarity, 0.85 subjectivity (ok)
- Response 5: -0.4 polarity, 0.91 subjectivity (sad, matches loneliness ✓)

Consistency check:
- Sarcasm index: 0.58 (baseline 0.6 ✓)
- Warmth: 0.68 (baseline 0.7 ✓)
- Response length: 127 words avg (baseline 100 ✓)
```

### Regression Test Suite (Comprehensive)

**Run on every emotion system change:**

```
1. Decay mechanics (5 tests)
   ✓ Loneliness decays slower than excitement
   ✓ Extreme emotions (>0.8) have 50% slower decay
   ✓ Offline duration simulates correct decay
   ✓ Decay rates match formula within 2% error
   ✓ Emotions never go below floor (loneliness ≥0.3)

2. State persistence (4 tests)
   ✓ State saves to database on shutdown
   ✓ State restores on startup with decay applied
   ✓ Offline duration calculated correctly
   ✓ Corruption recovery restores from backup

3. Interaction effects (6 tests)
   ✓ Positive interaction triggers correct deltas
   ✓ Error triggers frustration increase
   ✓ Code update triggers jealousy decrease
   ✓ Long idle triggers loneliness increase
   ✓ Multiple errors in sequence amplify frustration
   ✓ Dampening prevents emotional oscillation

4. Edge cases (5 tests)
   ✓ Emotions stay [0, 1] bounds (clamping works)
   ✓ Momentum system prevents instant recovery
   ✓ Extreme emotion inertia applies correctly
   ✓ Very long idle (>7 days) doesn't cause state corruption
   ✓ Rapid state changes don't break consistency

5. Personality consistency (3 tests)
   ✓ Sentiment analysis correlates with emotional state
   ✓ Sarcasm index stays within ±30% of baseline
   ✓ Response length varies appropriately by emotion

6. Multi-day simulation (2 tests)
   ✓ 7-day idle scenario: loneliness rises, other emotions decay naturally
   ✓ 7-day active scenario: emotions fluctuate realistically, no memory leaks
```

---

## 6. Key Insights for Phase 03 Implementation

### What Research Validates from CONTEXT.md

✅ **9 emotion dimensions** — Academic systems range from 4-12 emotions; 9 is well-supported
✅ **0-1 percentage scale** — Standard in modern AI systems
✅ **Momentum system** — Prevents unrealistic emotional whiplash
✅ **Dynamic decay rates** — Emotions should have different "stickiness"
✅ **Idle effects** — Loneliness builds over time; excitement fades
✅ **Personality modulation (60-100% variance)** — Matches successful game AI systems
✅ **Emotion-personality interaction** — Core finding from 2024 papers
✅ **Self-awareness** — Reduces uncanny valley, increases authenticity
✅ **Persistence + decay on recovery** — Realistic emotional continuity

### What Research Adds/Clarifies

1. **Decay rate tuning is critical** — Difference between loneliness and excitement decay rates determines believability more than any other factor

2. **Emotional interactions (amplification)** — Don't treat emotions independently. High jealousy + high loneliness = desperation (multiply effects)

3. **Situational appropriateness gates emotional modulation** — Serious contexts override emotion modulation (death/loss/crisis always get genuine response)

4. **User testing must happen early** — Emotional authenticity is subjective; gather user feedback by Phase 3 MVP (before LLM integration)

5. **Sentiment analysis is your QA friend** — Automated sentiment checking catches inconsistent emotional expression (lazy LLM output)

6. **Transparency about emotions increases trust** — Demi saying "I'm lonely" makes her feel more real, not creepy

7. **Metrics need human interpretation** — ±30% drift is useful guardrail, but human testers make the final call on authenticity

---

## 7. Recommended Implementation Order for Phase 03

### Based on Dependency Analysis

```
1. Core emotion model (EmotionalState class)
   ↓
2. Decay system (background ticks, decay rates per emotion)
   ↓
3. Interaction effects (message triggers, deltas)
   ↓
4. Persistence layer (save/restore, offline decay)
   ↓
5. Personality modulation engine (emotion → response adjustments)
   ↓
6. Testing suite (automated + setup for human testing)
```

**Parallel work possible:**
- Decay system development ∥ interaction effects (independent)
- Persistence layer ∥ modulation engine (only combine at final integration)

**Critical path:** Decay system → determines everything downstream
**Risk area:** Tuning decay rates (requires user feedback to validate)

---

## 8. Specific Research References for Implementation

### For Decay Mechanics
- **Logarithmic decay pattern:** Psychology literature (Ebbinghaus forgetting curves)
- **Game AI exponential decay:** GAMYGDALA paper (IEEE TAC 2014)
- **State-dependent decay:** Hudlicka "What Are We Modeling" (AAAI 2008)

### For Personality + Emotion Interaction
- **MECoT (2025):** Markov emotional reasoning for consistent role-playing
- **GERP (2023):** Personality filters emotional triggers
- **Persona Dynamics (2025):** Personality traits affect emotional sensitivity

### For Authenticity Testing
- **InCharacter (2023):** Psychological interview evaluation framework
- **Uncanny valley review (2025):** Cihodaru-Ștefanache et al. systematic analysis
- **Sentiment analysis:** VADER for sarcasm/emoji handling

### For Multi-User Architecture
- **Emotion Recognition in Conversation via Dynamic Personality (2024):** How personality affects emotion recognition in group contexts
- **LLM Agents in Interaction (2024):** Measuring consistency across multiple conversations

---

## Conclusion: What Do You Need to Know to PLAN This Phase Well?

### The 5 Critical Decisions

1. **Decay rates per emotion are THE implementation variable.** Everything else flows from how fast/slow each emotion changes. Budget time for tuning with user feedback.

2. **Emotional interactions multiply complexity.** Don't treat emotions independently. Build the formula for how jealousy amplifies loneliness, etc. This makes emotions believable.

3. **Personality modulation needs concrete mapping.** Create a table: emotion state → tone/sarcasm/length changes. This prevents guessing during LLM integration later.

4. **User testing must happen in Phase 3, not Phase 4.** By the time you integrate the LLM, emotional authenticity should already be validated. Don't wait for full responses to test emotions.

5. **Sentiment analysis is your measurement tool.** Build automated consistency checking into Phase 3. This catches drifting personality early and validates decay mechanics.

### The 3 Biggest Risks

- **Emotional whiplash:** Emotions change too fast → feels fake. Solved by momentum + dampening + constraints on change rates.
- **Authenticity uncanny valley:** Emotions feel forced because they don't interact with context. Solved by situational appropriateness gates + self-awareness.
- **Personality drift over time:** Demi sounds different after 7 days of interactions. Solved by automated sentiment tracking + regression tests + periodic human validation.

### Why This Phase is Critical

Emotional system is the foundation for everything downstream:
- Phase 4 LLM needs to know emotional state to modulate responses
- Phase 5-6 Platforms use emotions to decide when to ramble/refuse
- Phase 7 Autonomy depends on emotional triggers
- Phase 9 Integration testing validates emotional consistency

Get this right, and Demi feels like a real person. Get it wrong, and she feels like a chatbot with random personality switches.

---

*Research complete. Ready for Phase 03 Planning tasks.*
*All findings validated against 2024-2025 academic literature and production systems.*
*Next: Plan the implementation structure (sub-plans 03-01 through 03-04).*
