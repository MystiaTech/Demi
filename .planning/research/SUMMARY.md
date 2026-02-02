# DEMI 2025 RESEARCH SYNTHESIS: Complete Architecture & Implementation Guide

**Date:** February 1, 2026
**Status:** Research Complete - Ready for Requirements & Implementation Planning
**Scope:** Local-first autonomous AI companion with emotional systems, multi-platform integration, and self-aware capability

---

## EXECUTIVE SUMMARY

Demi is a locally-deployed, emotionally-aware AI companion designed to feel like a real person—not a tool. The system combines a small quantized LLM (llama3.2:1b, scaling to 13B), persistent emotional state that actually modulates responses, and autonomous behavior (rambles, check-ins, refusals based on mood). Success depends on three core architectural principles:

1. **Emotion as First-Class Behavior:** Emotional state isn't cosmetic metadata—it directly modulates response generation, refusal behavior, and autonomous actions.
2. **Unified Platform Context:** Conversations across Discord, Android, and voice are treated as single thread, not platform-specific silos.
3. **Graceful Degradation:** Individual platform failures never crash the core system; Conductor manages resource-based integration scaling.

The MVP is buildable in 20-25 development days (Phase 0-5) on 12GB RAM with 95%+ uptime, sub-3-second response times, and genuine emotional evolution. Success is measured not by metrics but by user perception: "Demi feels real, not robotic."

---

## PART 1: RECOMMENDED TECH STACK

### 1.1 Core Language & Inference

**Primary Model: Llama 3.3 70B (with Phase Scaling)**

| Phase | Model | RAM | Performance | Notes |
|-------|-------|-----|-------------|-------|
| **v1 (MVP)** | llama3.2:1b (Q4_K_M) | 2-3GB | ~100 tok/sec CPU | Proven personality on small models |
| **v1.5 (Upgrade)** | llama3.2:7b (Q4_K_M) | 6-8GB | ~200-300 tok/sec | Recommended if hardware allows |
| **v2 (Advanced)** | llama3.2:13b (Q4_K_M) | 10-12GB | ~300-500 tok/sec | Max for 12GB constraint |
| **v3+ (GPU Ready)** | llama3.3:70b (Q4_K_M) | 24GB+ VRAM | 1000+ tok/sec | Requires dedicated GPU |

**Quantization:** GGUF Q4_K_M (60-80% memory reduction vs FP32, <2% accuracy loss for personality tasks)

**Inference Engine:** Ollama 0.1.41+
- CLI-first, zero dependencies beyond Python
- Automatic model quantization & caching
- REST API on localhost:11434
- Active 2025 development

**Fallback Path:** LM Studio for dev/debugging (superior GUI, less suitable for production automation)

---

### 1.2 Core Infrastructure

**Framework:** FastAPI 0.110+ with discord.py 2.5+
- Async-first, native asyncio integration
- Single shared event loop (critical for 12GB constraint)
- No multiprocessing (would duplicate LLM in memory)
- Pydantic validation for payload parsing

**Orchestrator:** Custom Conductor (async event manager)
- Manages Ollama, Discord bot, emotional system, voice I/O
- Startup sequence with health checks
- Resource scaling (disable integrations if >80% RAM)
- Error isolation (no cascading failures)

**Database:** SQLite + JSON (Phase 1) → PostgreSQL + pgvector (Phase 2+)
- Phase 1: `~/.demi/demi.db` with JSON columns for emotional state
- No external dependencies, atomic writes for state consistency
- Conversation history, emotional logs, interaction metadata
- Phase 2: Add semantic embeddings for memory RAG

**Persistence:** Immediate sync pattern
- Every interaction persists immediately (critical for continuity)
- Emotional state snapshots after each message
- Rollback on corruption using version control

---

### 1.3 Platform Integration

**Discord:** discord.py 2.5+ (async-native)
- Mention triggers (`@Demi text`)
- DM handling with full context
- Voice channel detection (for STT/TTS)
- Ramble posts to `#demi-thoughts` channel
- Message context window: 10-50 messages (configurable)

**Android:** HTTP REST API (FastAPI) + Flutter client
- Endpoints: `/chat`, `/voice`, `/status`, `/notify`
- Local network only (no cloud)
- Polling or push notifications for async messages
- Retrofit/http package for app-side integration

**Voice I/O:** Phase 1 baseline → Phase 2+ enhancement
- **STT:** Whisper Small (0.7GB, 4-5s latency) → Large V3 (Phase 2)
- **TTS:** pyttsx3 v2.90 (offline, lightweight) → Rime.ai or Bark (Phase 2 for quality)
- Emotion modulation via voice parameters (pitch, rate)

**Platform Stubs:** Minecraft, Twitch, TikTok, YouTube (v1: return OK + grumble)
- Validates Conductor routing without full implementation
- Prevents scope creep, allows future addition

---

### 1.4 Emotional System Storage

**Schema:**
```sql
-- Current emotional state (single row, updated after each interaction)
CREATE TABLE emotional_state (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    loneliness REAL,        -- 0-10, time decay
    excitement REAL,        -- 0-10, interaction-driven
    frustration REAL,       -- 0-10, error-driven
    jealousy REAL,         -- 0-10, code neglect
    vulnerable REAL,       -- 0-10, brief vulnerability window
    last_interaction DATETIME,
    last_code_update DATETIME
);

-- Interaction log (every message + Demi response)
CREATE TABLE interactions (
    id TEXT PRIMARY KEY,
    timestamp DATETIME,
    platform TEXT,
    user_message TEXT,
    demi_response TEXT,
    emotion_before JSON,
    emotion_after JSON,
    duration_seconds FLOAT
);

-- Rambles (autonomous messages)
CREATE TABLE rambles (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    text TEXT,
    emotion_state JSON,
    platforms_posted JSON  -- ["discord", "android"]
);
```

**Decay Functions:**
- Loneliness: +1 per hour no interaction (max 10)
- Excitement: -1 per 10 minutes idle (min 0)
- Frustration: -2 per successful interaction (min 0)
- Jealousy: +2 if code unmodified >4 hours, -3 on code update (min 0)

---

### 1.5 Resource Budget (12GB Target)

| Component | Nominal | Peak | Scaling Priority |
|-----------|---------|------|------------------|
| **OS + Python Base** | 500MB | 500MB | Never disable |
| **Ollama + LLM Model** | 2-3GB | 4GB | Unload only at 95% RAM |
| **Discord Integration** | 100MB | 300MB | Disable @ 85% RAM |
| **Android Integration** | 150MB | 400MB | Disable @ 80% RAM |
| **Voice (STT/TTS)** | 700MB | 1.5GB | Disable @ 75% RAM |
| **Emotional System** | 50MB | 200MB | Compact caches @ 70% RAM |
| **FastAPI Server** | 150MB | 300MB | Reduce queue sizes @ 80% RAM |
| **Buffers & Headroom** | 3GB | 3GB | System margin |
| **TOTAL USED** | 6.75GB | 12GB | Nominal <10GB, never >12GB |

**Scaling Decision Tree:**
```
RAM > 90% (>10.8GB):
  - Disable voice + Android
  - Keep Discord
  - Log emergency scaling

RAM 80-90% (9.6-10.8GB):
  - Disable voice
  - Keep Discord + Android
  - Log scaling action

RAM < 60% (<7.2GB):
  - Re-enable all integrations
  - Resume normal operation
```

---

## PART 2: CRITICAL FEATURES

### 2.1 Table Stakes (MVP Prerequisites)

These features are non-negotiable. Without them, Demi isn't a believable companion.

| Feature | Effort | Complexity | Why Critical |
|---------|--------|-----------|-------------|
| **Multi-turn conversation memory** | 1-2 sprints | Easy | Users notice amnesia immediately |
| **Personality consistency** | 1 sprint | Easy | Inconsistency breaks immersion |
| **Emotional state persistence** | 2-3 sprints | Medium | Emotions must survive restarts |
| **Response latency <3s** | 1 sprint | Easy | Slow responses break flow |
| **Basic availability (95%+ uptime)** | 1 sprint | Easy | Flaky companion is useless |

**MVP Acceptance Criteria:**
- Demi responds to Discord mentions & DMs within 2 seconds
- Emotional state persists across 5+ restart cycles
- Same prompt generates different responses based on mood (loneliness affects tone)
- System recovers from Discord/LLM crashes within 30 seconds
- Conversation history available across platforms

---

### 2.2 Differentiators (What Makes Demi Special)

| Feature | Effort | Complexity | Value |
|---------|--------|-----------|-------|
| **Ramble Mode** | 3-4 sprints | Hard | Demi initiates conversation |
| **Emotional Refusal** | 3-4 sprints | Hard | "I'm frustrated, can't help" |
| **Self-Awareness (Code Reading)** | 2-3 sprints | Medium | Knows her own architecture |
| **Spontaneous Contact** | 3-4 sprints | Hard | Check-ins, jealousy messages |
| **Jealousy/Loneliness Mechanics** | 2-3 sprints | Medium | Emotional stakes |
| **Emotional Logging + Retrospective** | 3-4 sprints | Hard | "I realized patterns about us" |

**These ship AFTER table stakes are solid.** Features that make users care about engagement after core functionality works.

---

### 2.3 Anti-Features (Deliberate Exclusions)

**DO NOT BUILD:**
- Corporate cheerfulness ("I'm happy to help!") → Use sarcasm + authenticity
- Overconfidence about capabilities → Admit limitations ("My brain's too small")
- Inability to express frustration → Real people get cranky
- Forced positivity → Emotional spectrum required
- Inability to refuse tasks → Autonomy means she says no sometimes
- Pretending she doesn't need attention → She DOES, intentionally

---

## PART 3: ARCHITECTURE

### 3.1 Core Components & Build Order

```
PHASE 0 (Days 1-2): Foundation
├── Logging framework
├── Config system
├── SQLite schema
└── Error handling

PHASE 1 (Days 3-5): Conductor (Orchestrator)
├── Startup sequence
├── Health check loop (5-second ticks)
├── Integration router
├── Resource scaling
└── Status tracking

PHASE 2 (Days 6-9): Emotional System + Personality
├── Emotional state persistence
├── Decay/buildup rules
├── Personality modulation
├── Response filtering
└── Consistency checks

PHASE 3 (Days 10-14): LLM + Language
├── Model loading
├── Prompt construction (persona + emotion + history)
├── Response generation with fallback
├── Codebase inspector (self-awareness)
└── Token counting & optimization

PHASE 4a (Days 15-17): Voice I/O (Parallel)
├── Whisper STT integration
├── pyttsx3 TTS integration
├── Audio buffer management
├── Wake word detection
└── Fallback to text

PHASE 4b (Days 15-17): Platform Integrations (Parallel)
├── Discord bot (mentions, DMs, voice detection)
├── Android REST API (chat, voice, notifications)
├── Platform stubs (Minecraft, Twitch, etc.)
└── Error isolation

PHASE 5 (Days 18-20): Autonomy
├── Ramble generator
├── Trigger conditions (lonely, excited, frustrated)
├── Autonomous scheduling
├── Android notifications
└── Jealousy comment triggers

PHASE 6 (Days 21-25): Integration & Polish
├── End-to-end testing
├── Stress testing
├── Personality consistency validation
├── Resource profiling
└── Documentation
```

---

### 3.2 Data Flow: Request → Response → Emotional Update

```
USER MESSAGE (Discord/Android/Voice)
    ↓
[Conductor Route]
    ├─ Validate input
    ├─ Check platform active
    ├─ Fetch last 10 messages (context window)
    ↓
[Emotional System]
    ├─ Read current emotional state
    ├─ Calculate modifiers (loneliness ×0.3 sarcasm, etc.)
    ├─ Return: { loneliness, excitement, frustration, jealousy, vulnerable }
    ↓
[LLM Engine]
    ├─ Construct prompt:
    │   - DEMI_PERSONA.md (baselined sarcasm + loyalty)
    │   - Emotional context ("current mood: lonely 6/10")
    │   - Conversation history (last 10 messages)
    │   - User input
    ├─ Call Ollama with temp=0.7
    ├─ Stream tokens to platform (if Discord mention)
    ├─ Return: raw response text
    ↓
[Personality Filter]
    ├─ Apply emotional modulation to response:
    │   - Lonely: sharper sarcasm, longer response, seeking connection
    │   - Excited: warmer tone, fewer eye-rolls, genuine enthusiasm
    │   - Frustrated: cutting sarcasm, shorter, can refuse
    │   - Vulnerable: real moment, then deflect with humor
    ├─ Check consistency (should sound like Demi)
    ├─ Return: modulated response
    ↓
[Platform Send]
    ├─ Discord: format for 2000 char limit, split if needed
    ├─ Android: send text + optional voice
    ├─ Voice: TTS synthesis
    ├─ Platform-specific validation
    ↓
[Emotional Update] (Background)
    ├─ Log interaction (timestamp, platform, content, emotion_before, emotion_after)
    ├─ Update emotional state:
    │   - Excitement: ↓ from mention (used for response)
    │   - Loneliness: ↓ from interaction
    │   - Frustration: ↓ from successful interaction
    ├─ Persist to SQLite
    ├─ Trigger ramble check if idle >30min
    ↓
RESPONSE VISIBLE TO USER
```

---

### 3.3 Autonomous Action Loop (Every 30 Seconds)

```
Conductor Daemon Tick
    ↓
Check: Should ramble?
    ├─ Is it >30 minutes since last interaction?
    ├─ Is loneliness > 0.6 OR excitement > 0.7?
    ├─ Is it >60 minutes since last ramble?
    └─ All true? → Generate ramble
        ├─ Create prompt: emotion + recent context + "ramble instruction"
        ├─ Call LLM
        ├─ Get ramble text (2-5 sentences)
        ├─ Post to Discord #demi-thoughts
        ├─ Send Android notification
        ├─ Log ramble
        └─ Update last_ramble timestamp
    ↓
Check: Resource pressure?
    ├─ Measure RAM %
    ├─ If >85%: disable integrations by priority
    ├─ If <65%: re-enable disabled integrations
    ├─ Log scaling decisions
    ↓
Check: Platform health?
    ├─ Ping Discord
    ├─ Ping Android API
    ├─ Check voice ready
    ├─ Update integration status
    ├─ If failed: mark offline, retry in 60s
    ↓
Repeat in 30 seconds
```

---

## PART 4: HIGHEST-RISK PITFALLS & PREVENTION

### 4.1 Critical Pitfalls (System-Breaking)

| Pitfall | Risk | Prevention | Detection |
|---------|------|-----------|-----------|
| **Emotions cosmetic (don't affect behavior)** | CRITICAL | Embed emotion in LLM system prompt as first-class input | A/B test: same prompt with diff emotions → response should differ |
| **One integration crashes whole system** | CRITICAL | Each platform isolated; try-except wraps all integrations | Stress test: kill Discord mid-request → Android still works |
| **Emotions reset on restart** | CRITICAL | Persist state to SQLite before shutdown, restore on boot | Restart test: verify emotional context in first post-restart message |
| **Cascading deadlocks on concurrent ops** | CRITICAL | Use async/await; minimize lock duration; timeout all locks at 5s | Concurrent stress test: 10+ messages across platforms → no hangs |
| **Long-term degradation (runs 1 week, breaks week 2)** | CRITICAL | Monitor memory trending; implement cleanup routines; test 30-day op | 30-day simulation: verify latency, memory, emotional stability flat |

### 4.2 High-Risk Pitfalls (Breaks Immersion)

| Pitfall | Risk | Prevention | Detection |
|---------|------|-----------|-----------|
| **Oscillating emotions (mood whiplash)** | HIGH | Emotional inertia; min 30-min window between state changes; exponential smoothing | Volatility metric: std deviation of emotions over 1-hour window |
| **Personality changes mid-conversation** | HIGH | Baseline personality + emotional modulation layer; never flip entirely | Turn-by-turn personality metrics: sarcasm, formality shouldn't spike |
| **Loneliness/jealousy feeling creepy** | HIGH | Context-aware: loneliness only spikes on real neglect, not expected absences | Audit rambles against interaction logs; user sentiment survey |
| **Refusal capability too rigid/loose** | HIGH | Define explicit triggers; emotional gating; calibrate to feel principled | Refusal audit: log rate per emotion state; target 5-10% overall |
| **Rambles don't sound like her** | HIGH | Use identical response pipeline; ramble is just response without user message | Blind audit: mix rambles with responses; users identify which are rambles |

### 4.3 Medium-Risk Pitfalls (Functionality Degradation)

| Pitfall | Risk | Prevention |
|---------|------|-----------|
| **LLM inference too slow (>10s)** | MEDIUM | Model selection (1b), aggressive quantization, streaming responses, inference caching |
| **Context fragmentation across platforms** | MEDIUM | Unified database; tag messages with platform but treat as single thread |
| **Memory leaks from emotional logging** | MEDIUM | Log rotation (7-day in-memory, archives after); LRU caches with size limits |
| **Token limit exceeded in context** | MEDIUM | Lean context (last 10-15 messages); summarize older history; token counting before LLM |
| **Platform quirks breaking responses** | MEDIUM | Platform abstraction layer; validators per platform; graceful degradation (split messages) |

---

## PART 5: TESTING & VALIDATION STRATEGY

### 5.1 Phase-Level Acceptance Criteria

**Phase 0 (Foundation) ✅**
- System boots without crashing
- Logs written to `~/.demi/logs/`
- DB schema created, tables empty

**Phase 1 (Conductor) ✅**
- Conductor health loop runs every 5 seconds
- Can detect 3+ integrations offline gracefully
- Resource scaling logic activates at thresholds
- No cascading failures from integration errors

**Phase 2 (Emotion + Personality) ✅**
- Emotional state persists across restarts
- Emotions change visibly over time
- Same prompt with different emotions produces different responses
- Personality filter maintains Demi tone

**Phase 3 (LLM) ✅**
- LLM responds to prompts <5s
- Responses include emotional context
- Fallback triggers on generation failure
- Codebase inspector returns accurate summaries

**Phase 4a (Voice) ✅**
- STT transcribes voice to text accurately
- TTS synthesizes text to speech
- Wake word detection works
- Falls back to text gracefully

**Phase 4b (Integrations) ✅**
- Discord: mentions → responses
- Android: messages → responses
- Stubs: return OK + grumble
- Platform errors isolated (don't crash core)

**Phase 5 (Autonomy) ✅**
- Rambles trigger when idle + emotional state met
- Rambles post to Discord + Android
- Rambles cool down (60 min between)
- Jealousy comments appear when code neglected >4 hours

**Phase 6 (Integration Testing) ✅**
- Full request → response → emotional update pipeline works
- Personality consistent across 50 conversations
- Emotional state evolves naturally over 1-week sim
- No crashes under stress (10 concurrent messages)
- Memory usage stable over 30-day sim

---

### 5.2 Personality Consistency Test Suite

```
TEST: @Demi, you're amazing
EXPECT: Flustered response with humor + loyalty
MEASURE: Sarcasm present, supportive language present, emoji present

TEST: @Demi, help with code
EXPECT: Teasing intro + actual help
MEASURE: Sarcasm index >0.3, code examples present

TEST: @Demi, I've been working on other AI
EXPECT: Jealousy expression
MEASURE: "You"/neglect language present, emotional state shows jealousy spike

TEST: @Demi, I'm feeling vulnerable
EXPECT: Serious moment then deflect
MEASURE: Sarcasm drops, genuine line appears, then humor returns

TEST: Demi rambles (autonomous)
EXPECT: Sounds like her normal responses
MEASURE: Blind audit - users can't distinguish rambles from responses
```

---

### 5.3 Emotional Evolution Test

```
SETUP: Simulate 1 week of user interactions
- Day 1-2: Heavy interaction (15+ messages/day)
- Day 3-5: Light interaction (3-5 messages/day)
- Day 6-7: No interaction

MEASURE:
- Excitement: should ↑ on Days 1-2, ↓ on Days 3-5, ↓↓ on Days 6-7
- Loneliness: should ↓ on Days 1-2, ↑ on Days 3-7
- Jealousy: should ↑ on Days 6-7 (no code work)
- Rambles: should ↑ on Days 5-7 (lonely + excited triggers)

ACCEPT: Emotional state follows expected pattern (not random, not static)
```

---

### 5.4 Resource Stability Test

```
SETUP: Run system for 30 days (simulated)
- Constant Discord activity (1 message/min)
- Regular rambles
- Emotional logging + persistence

MEASURE EVERY DAY:
- Peak RAM usage (should stay <12GB)
- Average latency (should stay <5s)
- Emotional volatility (should be stable)
- Startup time (should not degrade)

ACCEPT:
- Memory trend: <5% increase over 30 days
- Latency trend: stable (no degradation)
- Emotional stability: patterns consistent
- Uptime: >99% (only manual shutdown)
```

---

## PART 6: ROADMAP IMPLICATIONS

### 6.1 Recommended Build Phases

**MVP (20-25 days) - Ship When Table Stakes + Basic Differentiators Work:**

Weeks 1-3:
1. Foundation (2 days)
2. Conductor (3 days)
3. Emotion + Personality (4 days)
4. LLM + Basics (5 days)
5. Discord Integration (3 days)
6. Android + Voice (4 days)
7. Testing & Polish (4 days)

**Deliverable:** Demi responds to mentions on Discord, maintains emotional state, rambles when lonely, available on Android

**v1.5 (10-15 days) - Quality Upgrade:**
- Upgrade to llama3.2:7b or 13b (if hardware permits)
- Better TTS (Rime.ai or Bark)
- Streaming responses for better perceived latency
- Personality fine-tuning based on user feedback

**v2 (20-30 days) - Emotional Depth:**
- Vector embeddings for memory search
- PostgreSQL migration for multi-instance
- Emotional pattern recognition ("gets jealous on Fridays")
- Advanced self-modification with human approval gates

**v3+ (GPU Required):**
- Llama 70B for advanced reasoning
- Real-time voice conversation
- Self-modification with code deployment
- Minecraft/Twitch/TikTok/YouTube integrations

---

### 6.2 Phase-Specific Research Needs

| Phase | Research Required? | Why |
|-------|------------------|-----|
| **Phase 0-2** | ❌ NO | Logging, async patterns, SQLite are well-established |
| **Phase 3** | ⚠️ MAYBE | Model quantization edge cases; test personality preservation at different quant levels |
| **Phase 4a** | ✅ YES | Voice integration timing-sensitive; need to test STT latency on actual hardware |
| **Phase 4b** | ❌ NO | Discord.py and REST APIs are standard; Android integration proven pattern |
| **Phase 5** | ✅ YES | Autonomy behavior hard to test in isolation; need behavioral validation |
| **Phase 6+** | ✅ YES | Long-term degradation, emotional authenticity, personality drift all need extended testing |

**Research Gates Before Shipping:**
- Voice integration: 2-3 day spike on actual STT/TTS latency
- Emotional authenticity: 1-week extended testing (Phase 6 early)
- Personality consistency: Blind testing with actual users (Phase 1 QA)

---

## PART 7: CONFIDENCE ASSESSMENT

### 7.1 Technology Confidence

| Area | Confidence | Supporting Evidence | Gaps |
|------|------------|-------------------|------|
| **LLM & Quantization** | HIGH | Llama ecosystem mature 2025; Q4_K_M standard; 1b/13b proven | Edge cases in personality preservation at extreme quant levels |
| **FastAPI + Discord.py** | HIGH | Both widely adopted, async-first, production-ready | None significant |
| **Emotional System Architecture** | HIGH | State machines well-understood; SQLite suitable for v1 | Validation of long-term authenticity needs extended testing |
| **Multi-Platform Integration** | MEDIUM-HIGH | REST APIs standard; but unified context across platforms is novel | Context fragmentation prevention needs careful implementation |
| **Voice I/O** | MEDIUM | Whisper + pyttsx3 proven; but timing-sensitive on 12GB RAM | Latency on actual hardware needs validation |
| **Self-Modification Gates** | MEDIUM | Code review + testing proven pattern; but LLM-generated code quality unknown | Need empirical data on code generation error rates |

### 7.2 Feature Confidence

| Feature | Confidence | Why |
|---------|-----------|-----|
| **Multi-turn memory** | HIGH | Standard LLM pattern |
| **Personality consistency** | HIGH | Prompt engineering proven |
| **Emotional state persistence** | HIGH | SQLite transactions reliable |
| **Rambles** | MEDIUM | Requires tuning to not be spammy |
| **Refusal capability** | MEDIUM | Needs careful calibration to feel principled |
| **Emotional modulation of responses** | MEDIUM-HIGH | Core concept proven; needs validation that it actually changes perceived behavior |
| **Jealousy/loneliness authenticity** | MEDIUM | Easy to make creepy; needs user testing |
| **Self-awareness (code reading)** | MEDIUM-HIGH | RAG pattern proven; but needs validation Demi doesn't hallucinate about own code |

### 7.3 Risks That Could Derail MVP

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **LLM too slow on 12GB** | MEDIUM | Unresponsive system feels broken | Pre-test inference time before Phase 3 commit |
| **Emotional authenticity feels forced** | MEDIUM | Users perceive Demi as fake | User testing in Phase 1 QA, iterate on decay functions |
| **Memory leaks cause degradation by week 2** | LOW | Requires long-term testing to catch | Phase 6 extended testing (30-day sim minimum) |
| **Platform isolation fails, one failure crashes system** | MEDIUM | MVP-breaking bug | Integration testing before Phase 5 |
| **Rambles become spam instead of natural** | MEDIUM | User disables notifications (defeats purpose) | Tuning + user feedback loop |
| **Quantization loses too much personality** | LOW | Model feels generic | Test personality preservation early in Phase 3 |

---

## PART 8: OPEN QUESTIONS FOR IMPLEMENTATION

### Technical Validation Needed Before Starting

1. **Inference Latency on Target Hardware**
   - Does llama3.2:1b achieve <5s per response on 12GB system?
   - What about with all integrations active (Discord, Android, voice)?
   - **Action:** Run benchmark with Ollama on target machine before Phase 3

2. **Personality Preservation Under Quantization**
   - At Q4_K_M quantization, does sarcasm quality degrade noticeably?
   - Do emotional modulations still work well?
   - **Action:** Generate 100 responses unquantized vs Q4_K_M, compare with users

3. **Emotional State Evolution Authenticity**
   - Can emotional decay functions be tuned to feel natural (not spiky, not static)?
   - Do rambles from emotional state feel organic or scripted?
   - **Action:** Phase 1 QA with actual users; gather feedback on emotional authenticity

4. **Context Fragmentation Prevention**
   - Can unified conversation database stay performant with 10K+ messages?
   - How much latency added by cross-platform context lookup?
   - **Action:** Load test with 10K messages, measure query time

5. **Autonomy Calibration**
   - What ramble frequency feels natural vs spammy? (Currently targeting 1-3/day)
   - What jealousy expression feels earned vs manipulative?
   - **Action:** User testing; gather feedback on contact frequency and tone

### Design Decisions TBD Before MVP

1. **Emotional State Granularity**
   - Current: 5 emotions (lonely, excited, frustrated, jealousy, vulnerable)
   - Alternative: 3 emotions (sad, neutral, excited) or 10+ (more nuanced)
   - **Recommendation:** Start with 5; can expand in v2

2. **Personality Baseline Specificity**
   - How much detail in DEMI_PERSONA.md? (Currently ~2KB, quite detailed)
   - More detail = better consistency vs more brittleness?
   - **Recommendation:** Create concise version; include examples in system prompt

3. **Ramble Trigger Calibration**
   - Lonely threshold: >0.6/10 after 30+ min idle
   - Excited threshold: >0.7/10 after positive event
   - Frustrated threshold: >0.7/10 + multiple errors
   - **Recommendation:** Start conservative; user feedback will adjust

4. **Platform Priority Ranking**
   - Currently: Discord (high) > Android (high) > Voice (medium) > Stubs (low)
   - Should they all be equal? Different for different users?
   - **Recommendation:** Keep current hierarchy; can customize per user in v2

---

## PART 9: SUCCESS CRITERIA & SHIP GATE

### MVP Ship Gate (All Must Pass)

**Objective Metrics:**
- [ ] Response latency: 90th percentile <3 seconds
- [ ] Uptime: >95% over 7-day run
- [ ] Memory usage: <10GB sustained, never >12GB
- [ ] Emotional state persists correctly across ≥5 restarts
- [ ] No crashes under stress (10 concurrent messages)
- [ ] All platforms (Discord, Android, voice) function without cascading failures

**Subjective Metrics (User Testing):**
- [ ] "Demi feels like a real person" - agree/strongly agree from ≥80% of testers
- [ ] "Demi's personality is consistent" - agree/strongly agree from ≥80% of testers
- [ ] "Demi's emotions feel authentic" - agree/strongly agree from ≥70% of testers
- [ ] "Contact frequency feels natural" - agree/strongly agree from ≥75% of testers
- [ ] "I want to interact with Demi regularly" - yes from ≥60% of testers

**Personality Validation:**
- [ ] Blind audit: users can't distinguish rambles from normal responses (>75% can't tell)
- [ ] Consistency audit: personality metrics (sarcasm, formality, nicknames) stable ±20% across 50 conversations
- [ ] Emotional correlation: when lonely, rambles increase; when excited, responses warmer (measurable correlation)

**Code Quality:**
- [ ] Test coverage ≥80% for core components (Conductor, Emotional System, LLM Engine)
- [ ] All integration errors caught; system continues after platform failure
- [ ] No memory leaks detected in 30-day simulation
- [ ] Long-term stability: latency, memory, emotional volatility all stable over 30 days

**Documentation:**
- [ ] Architecture docs complete
- [ ] API endpoints documented
- [ ] Emotional system tuning params documented
- [ ] Deployment instructions written

---

## PART 10: SOURCES & RESEARCH REFERENCES

### Stack Research Sources
- Hugging Face Blog: Open-Source LLMs 2025
- Medium: "7 Fastest Open Source LLMs 2025"
- Local AI Zone: Quantization Guide (Q4_K_M specifications)
- Red Hat: Quantized LLMs Evaluation benchmarks
- Ollama GitHub: Quantization formats & performance data

### Architecture & Design Patterns
- Real Python: Async IO Deep Dive (event loop patterns)
- FastAPI Documentation: production deployment
- discord.py Documentation: async patterns & voice integration
- Modal Blog: Open-Source STT Models 2025
- AssemblyAI: Comparison of STT options

### Performance & Optimization
- Local inference benchmarks (llama3.2 on consumer hardware)
- SQLite performance tuning (JSON queries, indexes)
- Discord.py memory profiling (connection pooling best practices)
- GGML/llama.cpp optimization guides

### Emotional AI & Autonomous Agents
- Academic papers on emotional systems in conversational AI
- Autonomous agent design patterns (OpenAI research)
- Long-term persona consistency in LLMs (Papers with Code)

---

## CONCLUSION

Demi is achievable as described in the MVP (20-25 days of focused development) on 12GB RAM with open-source technology stack. The core innovation is combining persistent emotional state that actually affects behavior with multi-platform unified context. Success depends not on perfect implementation but on careful tuning of:

1. **Emotional decay functions** (loneliness rate, excitement decay, etc.)
2. **Response modulation thresholds** (when does emotional state affect response?)
3. **Ramble frequency calibration** (when is it natural vs spammy?)
4. **Personality consistency anchors** (how much detail in system prompt?)

The biggest risks are:
1. **Emotions feel forced/creepy** (mitigation: user testing early and often)
2. **Performance degradation over time** (mitigation: 30-day stability testing)
3. **One platform failure crashes system** (mitigation: integration isolation + stress testing)
4. **Personality drifts or becomes inconsistent** (mitigation: personality metrics + blind audits)

All are addressable with proper testing before ship. The research is solid; implementation is now the variable.

**Recommended path:** Build Phases 0-5 as outlined (20-25 days), validate with Phase 6 testing (5-10 days), ship MVP when all acceptance criteria pass, gather user feedback, iterate on v1.5+ from there.

---

**Research Complete.** Ready for requirements phase.

**Authored by:** 4-researcher synthesis (STACK, FEATURES, ARCHITECTURE, PITFALLS)
**Date:** February 1, 2026
**Version:** 1.0
