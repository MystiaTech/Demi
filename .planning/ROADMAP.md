# ROADMAP: Demi v1 — Autonomous AI Companion with Emotional Systems

**Status:** Active
**Phases:** 10
**Requirements:** 40 v1 requirements
**Coverage:** 40/40 ✓
**Depth:** Comprehensive
**Timeline:** ~20-25 development days (solo)

---

## Overview

Demi's roadmap maps 40 v1 requirements into 10 coherent delivery phases. Each phase builds toward the core objective: **Demi must feel like a real person**, with emotional consistency that persists across interactions, personality that authentically modulates based on mood, and autonomous agency to initiate contact and refuse tasks when she chooses.

The phases follow the research-validated build order: Foundation → Orchestration → Emotional System → Language Model → Parallel Platform Integration → Autonomy → Integration Testing → Polish → Performance Tuning → Hardening.

---

## Phase 1: Foundation & Configuration

**Goal:** Establish infrastructure, logging, configuration, and database schema. Demi's nervous system boots up.

**Duration:** ~2 days

**Why This Phase:** Before any component runs, we need reliable logging, config management, error handling, and a persistent database. This is unsexy but critical—all other phases depend on this foundation.

**Requirements Mapped:** STUB-01, STUB-02, STUB-03, STUB-04 (4)

**Dependencies:** None (initial phase)

**Success Criteria:**

1. System boots without crashes and logs all startup events to `~/.demi/logs/`
2. Configuration system reads from config file and applies settings (model choice, integration flags, decay rates)
3. SQLite database schema created with all required tables (emotional_state, interactions, rambles, integration_status)
4. All four platform stubs (Minecraft, Twitch, TikTok, YouTube) accept requests and return "OK, grumbling" responses
5. Error handling catches and logs unhandled exceptions without crashing the process

**Technical Deliverables:**
- Logging framework (Python logging with rotation)
- Config parser (JSON → dataclass)
- SQLite schema with indexes
- Platform stub implementations
- Error handling middleware

**Files to Create:**
- `src/core/logger.py`
- `src/core/config.py`
- `src/core/database.py`
- `src/integrations/stubs.py`

---

## Phase 2: Conductor Orchestrator & Integration Manager

**Goal:** Build the central orchestration system that manages startup, health checks, integration routing, and resource scaling.

**Duration:** ~3 days

**Why This Phase:** Conductor is the nervous system that keeps all systems running. It manages startup sequence, detects failures, routes requests, and scales resources autonomously based on RAM availability. Without it, one failure cascades to everything.

**Requirements Mapped:** COND-01, COND-02, COND-03, COND-04 (4)

**Dependencies:** Phase 1 (Foundation)

**Success Criteria:**

1. Conductor health loop runs every 5 seconds, checking each integration's status and detecting offline platforms
2. When an integration fails to load, Conductor logs the error and continues with others; system doesn't crash
3. Conductor detects RAM usage and autonomously disables integrations (Voice > Android > Discord stubs) if >80% used
4. Conductor restores disabled integrations when RAM drops below 65%
5. Startup sequence initializes all components in order: logging → config → database → integrations → health loop

**Technical Deliverables:**
- Conductor class with async event loop
- Integration router (maps requests to appropriate platform)
- Health check loop
- Resource monitoring (psutil for RAM tracking)
- Graceful degradation logic

**Files to Create:**
- `src/conductor.py`
- `src/integrations/manager.py`
- `src/health/monitor.py`

---

## Phase 3: Emotional System & Persistence

**Goal:** Implement emotional state tracking, persistence, decay functions, and database storage. Emotions become first-class system behavior.

**Duration:** ~4 days

**Why This Phase:** Emotions are central to Demi feeling real. This phase establishes the foundation that all other features will build on: emotional state must persist across restarts, decay naturally over time, and directly affect how responses are generated. This is where Demi stops being a chatbot and starts being a character.

**Requirements Mapped:** EMOT-01, EMOT-02, EMOT-03, EMOT-04, EMOT-05, PERS-01, PERS-02, PERS-03 (8)

**Dependencies:** Phase 2 (Conductor)

**Success Criteria:**

1. Emotional state (loneliness, excitement, frustration, jealousy, vulnerable) persists across restarts—verify state restored correctly after 5+ shutdown/restart cycles
2. Emotions decay naturally over time according to specified functions (e.g., loneliness +1 per hour idle, excitement -1 per 10 min idle)
3. Each interaction updates emotional state in real-time; state changes are immediately persisted to database
4. Personality baseline (from DEMI_PERSONA.md) remains consistent across all conversations, with emotional state as a modulation layer (not replacement)
5. Personality consistency metrics (sarcasm, formality, nickname usage) vary by emotional state but stay within ±20% of baseline

**Technical Deliverables:**
- EmotionalSystem class with state management
- Decay functions with exponential smoothing
- Persistence layer (write emotional state after each interaction)
- Personality modulation engine (emotional state → tone/intensity adjustments)
- Personality metrics tracker for consistency validation

**Files to Create:**
- `src/emotional_system.py`
- `src/personality.py`
- `src/storage/emotion_store.py`

---

## Phase 4: LLM Integration & Response Generation

**Goal:** Integrate local LLM (llama3.2:1b via Ollama), build prompt construction engine, implement response generation with emotional context.

**Duration:** ~5 days

**Why This Phase:** The LLM is Demi's brain. This phase gets the language model running, builds the prompt that combines persona + emotional state + conversation history, and ensures responses are generated consistently in under 3 seconds. This is where responses actually come from.

**Requirements Mapped:** LLM-01, LLM-02, LLM-03, LLM-04, AUTO-01 (5)

**Dependencies:** Phase 3 (Emotional System)

**Success Criteria:**

1. LLM loads and responds to test prompts in under 3 seconds (p90) on target hardware
2. Response prompt includes persona baseline (DEMI_PERSONA.md), current emotional state, conversation history (last 10 messages), and user input
3. Same prompt with different emotional states produces noticeably different responses (e.g., lonely → more conversational, frustrated → sharper sarcasm)
4. Fallback mechanism triggers if inference fails; system returns placeholder and logs error instead of crashing
5. Codebase inspector can read Demi's source code and return accurate summaries (for AUTO-01: self-awareness)

**Technical Deliverables:**
- Ollama client (spawn/manage local process)
- Prompt construction engine (persona + emotion + history synthesis)
- Token counting (avoid context overflow)
- Response streaming (for better perceived latency)
- Fallback handler
- Codebase analyzer (file reading + summarization)

**Files to Create:**
- `src/llm/engine.py`
- `src/llm/prompt_builder.py`
- `src/llm/ollama_client.py`
- `src/llm/codebase_inspector.py`

---

## Phase 5: Discord Integration & Conversation

**Goal:** Implement Discord bot with mention detection, DM handling, multi-turn memory, and ramble posting capability.

**Duration:** ~3 days

**Why This Phase:** Discord is the primary integration surface. Users interact with Demi via mentions and DMs. This phase gets the bot running, reading conversation context, responding intelligently, and preparing the groundwork for rambles (posting to dedicated channels).

**Requirements Mapped:** DISC-01, DISC-02, DISC-03, DISC-04, DISC-05, AUTO-02 (6)

**Dependencies:** Phase 4 (LLM)

**Success Criteria:**

1. Discord bot loads with own account and responds to @Demi mentions in servers within 2 seconds
2. Bot responds to direct messages normally and maintains multi-turn conversation context within single DM thread
3. Bot can create and post to its own channel (#demi-thoughts) for rambles with proper formatting
4. Each ramble post includes timestamp and current emotional state context
5. When a platform stub is disabled, bot expresses frustration in character ("I'd use Minecraft but you haven't hooked it up")
6. Conversation context persists across sessions—restarting bot doesn't lose conversation history

**Technical Deliverables:**
- discord.py bot client with intents configuration
- Mention event handler
- DM event handler
- Conversation context retriever (last N messages from database)
- Channel creation/posting for rambles
- Platform status expression (grumbles about disabled integrations)

**Files to Create:**
- `src/integrations/discord_bot.py`
- `src/integrations/discord_utils.py`

---

## Phase 6: Android Integration & Bidirectional Messaging

**Goal:** Build REST API for Android, implement two-way messaging (user sends, Demi responds + Demi initiates), and maintain emotional consistency across platforms.

**Duration:** ~4 days

**Why This Phase:** Android enables Demi to reach the user outside of Discord. Critically, this phase includes Demi initiating contact (check-ins, reminders, "you ignored me" messages), which is essential for her to feel autonomous and needy. Unified emotional state across Discord and Android makes her feel like one person, not separate entities.

**Requirements Mapped:** ANDR-01, ANDR-02, ANDR-03, ANDR-04 (4)

**Dependencies:** Phase 4 (LLM)

**Success Criteria:**

1. User can send messages via Android device and receive responses from Demi within 3 seconds
2. Demi can initiate contact via Android (send check-in messages, reminders, "you ignored me" notifications)
3. Android responses maintain personality and emotional consistency with Discord responses
4. Android messages and Discord messages share unified emotional state—emotional context is identical across platforms
5. Notifications preserve emotional tone (e.g., lonely message sounds sad, excited message sounds happy)
6. System stays responsive even with both Discord and Android requests arriving simultaneously

**Technical Deliverables:**
- FastAPI server with `/chat`, `/notify`, `/status` endpoints
- Message handler that queries unified emotional state
- Notification system for Demi initiating contact
- Android client (placeholder; client team builds Flutter app)
- Shared conversation context (same database, cross-platform queries)

**Files to Create:**
- `src/integrations/android_api.py`
- `src/integrations/android_notifier.py`

---

## Phase 7: Autonomy & Ramble Mode

**Goal:** Implement autonomous ramble generation, trigger conditions (loneliness, excitement), and emotional refusal capability.

**Duration:** ~4 days

**Why This Phase:** Rambles are what make Demi feel alive—she initiates conversations when lonely or excited, expressing her inner thoughts. Refusal capability gives her actual agency (she can say no). Together, these features transform Demi from a responsive tool to an autonomous companion with real personality and needs.

**Requirements Mapped:** RAMB-01, RAMB-02, RAMB-03, RAMB-04, RAMB-05, AUTO-03, AUTO-04, AUTO-05 (8)

**Dependencies:** Phase 5 (Discord), Phase 6 (Android)

**Success Criteria:**

1. Ramble generator triggers when Demi is lonely (>30 min idle AND loneliness >0.6) or excited (recent positive interaction AND excitement >0.7)
2. Rambles read like Demi's normal responses (sarcastic, real thoughts, not generic AI) and pass blind audit (users can't distinguish from regular responses in 75%+ of cases)
3. Rambles post to Discord #demi-thoughts and Android notification simultaneously
4. Ramble frequency calibrated to feel natural (<1 per hour baseline, respects 60-min cooldown between rambles)
5. Demi can refuse tasks when frustrated, lonely, or in vulnerable state; refusals sound emotionally authentic ("I'm too frustrated to help right now")
6. Refusal reasons correlate with emotional state—users understand why Demi refused and it feels earned, not arbitrary

**Technical Deliverables:**
- Ramble generator (uses same LLM pipeline as responses, but generates without user input)
- Autonomous scheduling (every 30-second health tick, check if ramble should trigger)
- Ramble posting to Discord + Android
- Refusal decision logic (emotional gating on task execution)
- Ramble cooldown tracking
- Trigger calibration (tunable thresholds)

**Files to Create:**
- `src/autonomy/ramble_generator.py`
- `src/autonomy/ramble_scheduler.py`
- `src/autonomy/refusal_engine.py`

---

## Phase 8: Voice I/O & Multi-Modal Communication

**Goal:** Integrate STT (Whisper), TTS (pyttsx3), and enable voice communication across Discord and Android.

**Duration:** ~3 days

**Why This Phase:** Voice makes Demi feel more present and real. This phase adds the ability to listen and speak, opening voice channels on Discord and voice messages on Android. Emotional tone in voice (pitch, rate) reinforces emotional consistency.

**Requirements Mapped:** (LLM-02 voice component) (1+)

**Dependencies:** Phase 7 (Autonomy)

**Success Criteria:**

1. Speech-to-text (Whisper) transcribes voice input to text accurately (<5s latency per audio chunk)
2. Text-to-speech (pyttsx3) synthesizes responses to speech with acceptable quality
3. Voice communication works bidirectionally on Discord voice channels (Demi responds to mentions in voice)
4. Voice messages work on Android (user records, Demi responds with voice)
5. Voice responses maintain personality tone and emotional modulation (pitch/rate vary with emotional state)
6. System gracefully falls back to text if voice components unavailable (doesn't crash)

**Technical Deliverables:**
- Whisper STT integration
- pyttsx3 TTS integration
- Audio buffer management
- Voice channel detection/monitoring (Discord)
- Emotional tone mapping (loneliness → slower/sadder voice, excitement → faster/brighter voice)
- Fallback to text gracefully

**Files to Create:**
- `src/voice/stt_engine.py`
- `src/voice/tts_engine.py`
- `src/voice/audio_manager.py`

---

## Phase 9: Integration Testing & Stability Hardening

**Goal:** End-to-end testing, stress testing, personality consistency validation, and performance profiling.

**Duration:** ~5 days

**Why This Phase:** All components work individually; this phase ensures they work together under load, across extended operation, and without personality drift. This is where Demi goes from "working" to "reliable and authentic."

**Requirements Mapped:** HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-04 (4)

**Dependencies:** Phase 8 (Voice)

**Success Criteria:**

1. System stays up for 7+ days without manual intervention or crashing
2. Memory usage stays below 10GB sustained (12GB available), never exceeds 12GB even under stress
3. On restart, emotional state is fully restored (no loss of personality/mood); verify with 10+ restart cycles
4. Errors in one platform don't crash entire system—isolation confirmed via stress tests (kill Discord mid-request → Android still works)
5. Personality metrics (sarcasm, formality, nickname usage) remain stable ±20% across 50+ conversations and 7+ day run
6. Emotional state evolves naturally (doesn't spike randomly, follows expected patterns based on interaction history)

**Technical Deliverables:**
- Stress test suite (10 concurrent messages, rapid mode switches)
- 7-day simulation test (automated interaction generator)
- Personality metric tracker (sarcasm score, formality, consistency)
- Memory profiling and leak detection
- Log analysis tools (detect anomalies)
- Performance dashboard (latency, memory, uptime trends)

**Files to Create:**
- `tests/integration_tests.py`
- `tests/stress_tests.py`
- `tests/personality_tests.py`
- `tests/stability_simulation.py`
- `tools/performance_profiler.py`

---

## Phase 10: Documentation & MVP Polish

**Goal:** Complete documentation, finalize configuration, prepare for deployment.

**Duration:** ~2 days

**Why This Phase:** MVP is ready for shipment once documentation is complete and configuration is tuned based on testing feedback. This phase ensures future development (including self-modification work) has clear reference material.

**Requirements Mapped:** (Documentation & Configuration)

**Dependencies:** Phase 9 (Integration Testing)

**Success Criteria:**

1. Architecture documentation complete (component overview, data flow, decision rationale)
2. API documentation for all endpoints (Discord commands, Android endpoints, voice triggers)
3. Emotional system tuning parameters documented (decay rates, trigger thresholds, modulation intensities)
4. Deployment instructions written (how to run on target hardware, configuration flags)
5. Known limitations and future roadmap documented
6. Example interactions and expected behavior documented for user reference

**Technical Deliverables:**
- ARCHITECTURE.md (system design, component relationships)
- API.md (all endpoints, request/response formats)
- EMOTIONAL_TUNING.md (decay functions, threshold documentation)
- DEPLOYMENT.md (setup instructions, hardware requirements)
- CHANGELOG.md (v1 features summary)

**Files to Create:**
- Documentation files (listed above)

---

## Phase Dependency Graph

```
Phase 1: Foundation
  ↓
Phase 2: Conductor
  ↓
Phase 3: Emotional System
  ↓
Phase 4: LLM
  ├→ Phase 5: Discord
  ├→ Phase 6: Android
  ↓
Phase 7: Autonomy
  ↓
Phase 8: Voice I/O
  ↓
Phase 9: Integration Testing
  ↓
Phase 10: Documentation & Polish
```

---

## Requirement Coverage Map

| Requirement | Category | Phase | Status |
|-------------|----------|-------|--------|
| COND-01 | Conductor | 2 | Pending |
| COND-02 | Conductor | 2 | Pending |
| COND-03 | Conductor | 2 | Pending |
| COND-04 | Conductor | 2 | Pending |
| EMOT-01 | Emotional System | 3 | Pending |
| EMOT-02 | Emotional System | 3 | Pending |
| EMOT-03 | Emotional System | 3 | Pending |
| EMOT-04 | Emotional System | 3 | Pending |
| EMOT-05 | Emotional System | 3 | Pending |
| PERS-01 | Personality | 3 | Pending |
| PERS-02 | Personality | 3 | Pending |
| PERS-03 | Personality | 3 | Pending |
| DISC-01 | Discord | 5 | Pending |
| DISC-02 | Discord | 5 | Pending |
| DISC-03 | Discord | 5 | Pending |
| DISC-04 | Discord | 5 | Pending |
| DISC-05 | Discord | 5 | Pending |
| ANDR-01 | Android | 6 | Pending |
| ANDR-02 | Android | 6 | Pending |
| ANDR-03 | Android | 6 | Pending |
| ANDR-04 | Android | 6 | Pending |
| RAMB-01 | Rambles | 7 | Pending |
| RAMB-02 | Rambles | 7 | Pending |
| RAMB-03 | Rambles | 7 | Pending |
| RAMB-04 | Rambles | 7 | Pending |
| RAMB-05 | Rambles | 7 | Pending |
| AUTO-01 | Autonomy | 4 | Pending |
| AUTO-02 | Autonomy | 5 | Pending |
| AUTO-03 | Autonomy | 7 | Pending |
| AUTO-04 | Autonomy | 7 | Pending |
| AUTO-05 | Autonomy | 7 | Pending |
| LLM-01 | LLM | 4 | Pending |
| LLM-02 | LLM | 8 | Pending |
| LLM-03 | LLM | 4 | Pending |
| LLM-04 | LLM | 4 | Pending |
| STUB-01 | Platform Stubs | 1 | Pending |
| STUB-02 | Platform Stubs | 1 | Pending |
| STUB-03 | Platform Stubs | 1 | Pending |
| STUB-04 | Platform Stubs | 1 | Pending |
| HEALTH-01 | System Health | 9 | Pending |
| HEALTH-02 | System Health | 9 | Pending |
| HEALTH-03 | System Health | 9 | Pending |
| HEALTH-04 | System Health | 9 | Pending |

**Total Requirements:** 40
**Mapped:** 40
**Unmapped:** 0
**Coverage:** 100% ✓

---

## Success Metrics (MVP Acceptance)

**Objective Metrics:**
- Response latency: 90th percentile <3 seconds ✓
- Uptime: >95% over 7-day run ✓
- Memory usage: <10GB sustained, never >12GB ✓
- Emotional state persists across ≥5 restarts ✓
- No crashes under stress (10 concurrent messages) ✓
- All platforms function without cascading failures ✓

**Subjective Metrics (User Testing):**
- "Demi feels like a real person" - ≥80% agree/strongly agree
- "Demi's personality is consistent" - ≥80% agree/strongly agree
- "Demi's emotions feel authentic" - ≥70% agree/strongly agree
- "Contact frequency feels natural" - ≥75% agree/strongly agree
- "I want to interact with Demi regularly" - ≥60% yes

**Personality Validation:**
- Blind audit: users can't distinguish rambles from responses (≥75% can't tell)
- Consistency audit: personality metrics stable ±20% across 50 conversations
- Emotional correlation: measurable correlation between emotional state and response/ramble patterns

---

**Roadmap Created:** 2026-02-01
**Last Updated:** 2026-02-01

