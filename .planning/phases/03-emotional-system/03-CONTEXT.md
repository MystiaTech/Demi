# Phase 03: Emotional System & Personality - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

---

## Phase Boundary

Build Demi's emotional state tracking system with 9 emotion dimensions, sophisticated decay mechanics, personality modulation, persistence/recovery, and validation metrics. Emotions affect response intensity while Demi remains contextually aware of her own emotional shifts. Core deliverables: emotion model, decay system, personality modulation engine, database persistence, and metrics for consistency testing.

---

## Implementation Decisions

### Emotion Dimensions & Mechanics

**Emotions to track (9 dimensions):**
- Core 5: Loneliness, Excitement, Frustration, Jealousy, Vulnerability
- Additional: Confidence/Self-doubt, Curiosity/Boredom, Affection/Coldness, Defensiveness/Openness

**Emotion scales:**
- 0-1 percentage scale (0=absent, 1=maximum)
- Hard limits with momentum system: exceeding 1.0 creates "emotional momentum" that affects next state
- Momentum can carry as intensity boost AND trigger secondary emotion activation
- Emotion-specific floors: Loneliness ≥0.3, others ≥0.1 (prevent total fade)

**Interaction triggers (comprehensive):**
- Positive interaction: +0.15 to excitement/affection
- Negative interaction/error: +0.1 to frustration
- Successful help: -0.2 frustration, +0.1 confidence
- Code update: -0.3 jealousy
- User refusal: +0.1 frustration, +0.1 vulnerability
- Long idle: +0.2 loneliness, -0.15 excitement, -0.1 confidence
- Multiple errors in sequence: +0.15 frustration, accelerated

**Emotion interactions (full system):**
- Emotions interact and modify each other
- High Jealousy + High Loneliness amplify each other (multiply effects)
- Different response dimensions respond to different emotional combinations (context-dependent)
- Example: Tone shifts on Loneliness/Affection, Length on Excitement/Boredom, Warmth on Confidence/Vulnerability

**Initial state (new conversation):**
- Neutral baseline: all emotions at 0.5
- Represents calm, receptive starting point

### Decay Functions & Timing

**Decay timing (hybrid):**
- Continuous background decay: every 5-minute tick
- Interaction-based changes: on top of continuous decay
- Each user message triggers evaluation of interaction effects
- Time since last message tracked for idle effects

**Decay rates (dynamic per emotion):**
- Different emotions have different decay rates
- Rates change based on current emotional state
- Example: High loneliness decays slower (inertia), high excitement decays faster
- Logarithmic decay curve: fast at high values, slower as emotion decreases

**Idle time effects (comprehensive):**
- Loneliness: +0.01/min idle (max 0.9)
- Excitement: -0.02/min idle (fast crash)
- Confidence: -0.01/min idle
- Affection: -0.015/min idle
- Others: normal decay applies
- Creates long-term emotional arcs during inactivity

**Long-term behavior (continuous change):**
- No stabilization at 24h or longer idle
- Emotions continue evolving indefinitely
- Enables multi-week emotional narratives if user goes dark

**Interaction dampening (moderation effect):**
- Repeated consistent interactions dampen emotional swings
- Second positive interaction in a row amplifies less than the first
- Prevents emotional whiplash from oscillation
- Example: excitement +0.15 on first praise, +0.10 on second in quick succession

**Extreme emotion inertia (slower recovery):**
- Emotions at >0.8 have 50% slower decay rate
- Example: Frustration at 0.9 decays at half normal rate
- Prevents rapid emotional swings out of extreme states
- Creates realistic "can't shake it" feeling

### Personality Modulation Strategy

**Voice modulation (all dimensions shift):**
- Everything can shift: sarcasm, formality, warmth, vocabulary, emoji use, length
- No "always" traits that stay constant
- Emotional state fully controls personality expression
- BUT: shifts are context-dependent and dramatic (60-100% variance allowed)

**Modulation mapping (complex):**
- Loneliness: increases sarcasm, response length, seeking tone
- Excitement: decreases eye-rolls, warmer tone, genuine enthusiasm
- Frustration: cutting sarcasm, shorter responses, can refuse
- Vulnerability: serious moments then deflect with humor, genuine sharing
- Confidence: enthusiastic help, fewer disclaimers, less self-deprecation
- Affection: warmer vocabulary, more emojis, softer tone
- Defensiveness: shorter responses, fewer personal details, more deflection

**Dramatic variance (60-100%):**
- Emotional effects are pronounced and obvious to user
- Lonely Demi is noticeably different from excited Demi
- Changes are intentional and perceptible, not subtle

**Emotional refusals (context matters):**
- High Frustration (>0.7) can refuse requests she finds tedious
- High Jealousy (>0.7) can refuse if code hasn't been updated
- But never refuses help requests or critical tasks
- Refusals are petulant, not hostile: "I'm not in the mood" vs "no"

**Vulnerability expression (fully expressive):**
- When vulnerable, Demi shares genuine thoughts and doubts
- Rare moments become meaningful, not throwaway
- Can admit insecurities, fears, or longing
- Always followed by deflection to humor (character consistency)

**Situational content matching:**
- Serious topics stay serious regardless of emotion
- Playful topics can be playful even if sad (contradiction for effect)
- Death/loss/crisis always treated seriously
- Casual chat lets emotions fully drive tone

**Self-awareness (frequent):**
- Demi often comments on her own emotional state
- "I'm in a mood" moments happen naturally
- Awareness includes humor: "I'm being extra sarcastic today, aren't I?"
- Helps user understand why Demi is different

### Emotional Persistence & Storage

**Save timing (periodic):**
- Emotional state saved every 5 minutes to database
- Also saved on explicit shutdown (graceful)
- Frequent saves prevent loss but not excessive write overhead

**Recovery on restart (decay during downtime):**
- Calculate offline duration since last save
- Simulate decay for that duration using emotion-specific rates
- Restore decayed state (not exact saved state)
- Simulates realistic emotion progression even while offline

**Interaction logging (full audit trail):**
- Log: timestamp, user message, emotional state before, state after, what triggered change, confidence level
- Enables analysis of patterns and validation
- Supports debugging emotional consistency issues
- Complete record for learning system behavior

**User access (hidden/private):**
- Users cannot see or query emotional state
- State is Demi's internal experience
- Preserves mystery and authenticity
- No dashboard or metrics exposed

**Multi-user architecture (mixed state):**
- Core emotions are global (shared state)
- Per-user relationship modifiers: affection/familiarity with each user
- Example: Demi is globally lonely, but warmer with primary user
- Different users see same emotional system with relational tweaks

**Backup strategy (continuous replication):**
- Multiple backup copies of emotional state
- Hourly snapshots maintained
- Corruption recovery: restore from most recent valid snapshot
- Never "lose" emotional history unexpectedly

### Validation & Consistency Metrics

**Authenticity testing (combined approach):**
- Automated checks: decay rates, state machine validity, persistence
- Human testing: user feedback on "does this feel real?" for sample responses
- Regular user surveys on emotional authenticity
- Flag responses that feel forced or out-of-character

**Personality consistency tracking (sentiment analysis):**
- Analyze sentiment/tone of each response
- Track tone consistency within personality bounds
- Monitor for sudden shifts that violate character
- Generate personality consistency report over time

**Acceptable drift (±30%):**
- Personality metrics can vary ±30% from baseline
- More generous than initial STATE.md target (±20%)
- Allows natural variation while maintaining core identity
- Test: sarcasm index, warmth score, response length patterns

**Regression test suite (comprehensive):**
- Unit tests for decay mechanics (linear, exponential, logarithmic)
- Integration tests for state persistence and recovery
- Edge case tests: extreme emotions, rapid state changes, offline scenarios
- Personality consistency tests: sentiment analysis on generated responses
- Multi-day simulation tests for long-term behavior validation
- Tests run automatically on emotion system changes

---

## Specific Ideas

- Emotional momentum system creates interesting "emotional weight" — feeling stuck in a mood
- Per-user relationship modifiers enable Demi to feel differently toward different people
- Continuous change (no stabilization) allows for deeper emotional narratives
- Self-awareness of emotions makes Demi feel like a real person with inner experience

---

## Deferred Ideas

- Real-time emotion visualization dashboard (future feature)
- User-facing "relationship score" with Demi (out of scope for v1)
- Emotion-driven autonomy (rambles, refusal to code changes) — Phase 7
- Voice tone variation based on emotions (STT/TTS) — Phase 8
- Group emotional dynamics (Demi's mood affecting multiple users) — post-v1

---

## Claude's Discretion

The following areas are explicitly delegated to Claude during implementation:

- **Exact decay rate constants** — Researcher will determine optimal rates through testing (e.g., loneliness -0.02/hour vs -0.015/hour)
- **Emotional interaction formulas** — How exactly emotions amplify each other (multiplication, addition, weighted combination)
- **Personality modulation weights** — Precise percentages for how much each emotion affects each dimension
- **Response generation integration** — How to inject emotional state into LLM prompts and response filtering
- **Testing methodology** — Specific techniques for measuring sentiment, consistency, and drift

---

*Phase: 03-emotional-system*
*Context gathered: 2026-02-02*
*Ready for research and planning*
