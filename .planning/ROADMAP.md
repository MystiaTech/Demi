# ROADMAP: Demi v1 — Autonomous AI Companion with Emotional Systems

**Status:** In Progress

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

**Status:** Complete ✅
**Plans Created:** 4 (Configuration, Logging, Database, Services & Error Handling)

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

**Files Created:**
- `src/core/logger.py`
- `src/core/config.py`
- `src/core/database.py`
- `src/integrations/stubs.py`
- `src/core/error_handler.py`

**Plans:**
- [x] 01-01-PLAN.md — Configuration Management
- [x] 01-02-PLAN.md — Logging System
- [x] 01-03-PLAN.md — Database Integration
- [x] 01-04-PLAN.md — Platform Stubs & Error Handling

---

## Phase 2: Conductor Orchestrator & Integration Manager

**Goal:** Build the central nervous system that orchestrates startup, monitors health, manages resource scaling autonomously, routes requests between platforms, and ensures one failure cannot cascade through the system.

**Status:** Complete ✅
**Plans Created:** 5 (Plugin Architecture, Health Monitoring, Resource Scaling, Request Routing, Main Orchestrator)

**Duration:** ~3 hours (2026-02-02)

**Why This Phase:** The conductor enables Demi to manage her own capabilities autonomously, making decisions about which integrations to enable based on resources and health. This prevents crashes and enables graceful degradation.

**Requirements Mapped:** COND-01, COND-02, COND-03, COND-04 (4)

**Dependencies:** Phase 1 (Foundation)

**Success Criteria:**

1. ✅ Health monitoring runs 5-second checks with staggered execution and circuit breaker protection
2. ✅ Auto-scaling system disables integrations at 80% RAM, re-enables at 65% with predictive ML models
3. ✅ Request router distributes load across platform instances with dead letter queue for failures
4. ✅ Plugin system can dynamically discover, load, and manage platform integrations
5. ✅ Conductor orchestrator coordinates all subsystems with graceful startup/shutdown

**Technical Deliverables:**
- ✅ Async plugin architecture with entry point discovery
- ✅ Health monitoring with circuit breakers and Prometheus metrics
- ✅ Predictive auto-scaling with scikit-learn Linear Regression
- ✅ Request routing with load balancing and process isolation
- ✅ Main conductor orchestrator coordinating all components

**Files Created:**
- `src/platforms/base.py` - Platform interface
- `src/plugins/manager.py` - Plugin lifecycle management
- `src/conductor/health.py` - Health monitoring system
- `src/conductor/scaler.py` - Predictive auto-scaling
- `src/conductor/router.py` - Request routing system
- `src/conductor/orchestrator.py` - Main conductor
- `main.py` - Application entry point

**Plans:**
- [x] 02-01-PLAN.md — Plugin Architecture & Discovery ✅
- [x] 02-02-PLAN.md — Health Monitoring & Circuit Breakers ✅
- [x] 02-03-PLAN.md — Resource Monitoring & Predictive Scaling ✅
- [x] 02-04-PLAN.md — Request Routing & Isolation ✅
- [x] 02-05-PLAN.md — Main Orchestrator & Integration ✅

---

## Phase 3: Emotional System & Personality Modulation

**Goal:** Implement emotional state tracking, decay mechanics, personality modulation, and persistence. Demi develops genuine emotional complexity.

**Status:** Complete ✅
**Plans Created:** 4 (Emotional State, Decay Mechanics, Personality Modulation, Persistence)

**Duration:** ~4 hours (2026-02-02)

**Why This Phase:** Emotional system is the foundation for authentic responses. Without it, Demi is just a chatbot. This phase builds the core mechanics that make her feel real: emotions that evolve, decay naturally, and modulate her personality in consistent ways.

**Requirements Mapped:** EMOT-01, EMOT-02, EMOT-03, EMOT-04, EMOT-05, PERS-01, PERS-02, PERS-03 (8)

**Dependencies:** Phase 1 (Foundation), Phase 2 (Conductor)

**Success Criteria:**

1. ✅ Emotional state persists across sessions (loneliness, excitement, frustration, affection, confidence, curiosity, jealousy, vulnerability, defensiveness)
2. ✅ Emotions decay naturally over time (5-minute background ticks, emotion-specific decay rates)
3. ✅ Emotional state modulates response generation (8 response parameters: sarcasm, formality, warmth, response_length, enthusiasm, vulnerability, initiative, humor)
4. ✅ Personality remains consistent while emotions create variance (anchor + modulation model)
5. ✅ Emotional state stored/restored with offline decay simulation on startup

**Technical Deliverables:**
- ✅ EmotionalState class with 9 emotion dimensions
- ✅ Momentum tracking for cascade effects
- ✅ DecaySystem with emotion-specific decay rates
- ✅ InteractionHandler with 8 event types
- ✅ PersonalityModulator with 8 response parameters
- ✅ SQLite persistence with backup/recovery

**Files Created:**
- `src/models/emotional_state.py` - EmotionalState dataclass
- `src/models/decay_system.py` - Decay mechanics
- `src/conductor/personality_modulator.py` - Personality modulation
- `src/models/emotional_persistence.py` - Database persistence

**Plans:**
- [x] 03-01-PLAN.md — Emotional State Model & Core Mechanics ✅
- [x] 03-02-PLAN.md — Decay Mechanics & Interaction System ✅
- [x] 03-03-PLAN.md — Personality Modulation Engine ✅
- [x] 03-04-PLAN.md — Persistence Layer & Validation Framework ✅

---

## Phase 4: LLM Integration & Self-Awareness

**Goal:** Integrate local LLM (llama3.2:1b via Ollama), implement prompt building with emotional modulation, response generation, and Demi's self-awareness of her own codebase.

**Status:** Planning ⏳
**Plans Created:** 4 (Inference Engine, Prompt Building, Response Processing, Self-Awareness)

**Duration:** ~4 hours (estimated)

**Why This Phase:** LLM is the voice of Demi's personality. This phase connects everything: emotional state → prompt modulation → inference → response processing. Self-awareness (reading her own code) adds a unique dimension that enables future self-modification and introspective responses.

**Requirements Mapped:** LLM-01, LLM-02, LLM-03, LLM-04, AUTO-01 (5)

**Dependencies:** Phase 1 (Foundation), Phase 2 (Conductor), Phase 3 (Emotional System)

**Success Criteria:**

1. Responses generated by local llama3.2:1b model (quantized Q8_0)
2. Response generation time <3 seconds (p90) on target hardware
3. Emotional state embedded in system prompt for modulation (loneliness → longer/sharper, excitement → warmer, frustration → short/cutting)
4. Context window includes recent conversation history + emotional state + persona (~8K tokens max)
5. AUTO-01: Demi can read her own codebase and understand her own architecture

**Technical Deliverables:**
- OllamaInference class with async chat interface
- PromptBuilder with personality anchor + emotional modulation
- ConversationHistory with token-aware trimming
- ResponseProcessor for text cleaning and logging
- CodebaseReader for self-awareness
- Full end-to-end inference pipeline

**Files to Create:**
- `src/llm/__init__.py` - LLM module exports
- `src/llm/config.py` - LLM configuration
- `src/llm/inference.py` - Ollama integration
- `src/llm/prompt_builder.py` - Prompt construction with emotional modulation
- `src/llm/history_manager.py` - Conversation history management
- `src/llm/response_processor.py` - Response cleaning and logging
- `src/llm/codebase_reader.py` - Self-awareness / codebase introspection

**Plans:**
- [ ] 04-01-PLAN.md — Inference Engine & Context Management
- [ ] 04-02-PLAN.md — Prompt Building & Emotional Modulation
- [ ] 04-03-PLAN.md — Response Processing & Persistence
- [ ] 04-04-PLAN.md — Self-Awareness & Full Integration

---

## Phase 5: Discord Integration

**Goal:** Connect Demi to Discord as a bot. Implement mentions, DMs, conversation context, and ramble posting.

**Status:** Complete ✅
**Plans Created:** 3 (Bot Foundation, Response Formatting, Ramble System)

**Duration:** ~5 hours (2026-02-01 to 2026-02-02)

**Why This Phase:** Discord is Demi's primary platform. She needs to respond to mentions in servers and DMs, maintain multi-turn conversations, and post rambles to dedicated channels.

**Requirements Mapped:** DISC-01, DISC-02, DISC-03, DISC-04, DISC-05, AUTO-02 (6)

**Dependencies:** Phase 1, 2, 3, 4 (all foundation complete) ✅

**Technical Deliverables:**
- ✅ DiscordBot platform plugin with discord.py (async, non-blocking)
- ✅ Message handlers (mentions, DMs with typing indicators)
- ✅ Embed formatting with emotion-based colors (9 emotions → Discord colors)
- ✅ Ramble system (autonomous, emotion-triggered, 60-minute throttle)
- ✅ Database persistence for interactions and rambles

**Plans:**
- [x] 05-01-PLAN.md — Discord Bot Foundation (Message Routing) ✅
- [x] 05-02-PLAN.md — Response Formatting & Embed System ✅
- [x] 05-03-PLAN.md — Ramble Posting & Autonomy ✅

**Commits Created:**
- b19ee78: feat(05-01): Create DiscordBot platform plugin with intents and event handlers
- 6f897dd: feat(05-01): Implement message routing from Discord to Conductor LLM pipeline
- 766d75f: feat(05-01): Register DiscordBot in integrations module
- 4ff3259: docs(05-01): Complete Discord Bot Foundation plan
- b05463c: feat(05-02): Create emotion-to-color mapping and embed formatter
- a027103: feat(05-02): Update on_message handler to use embed formatting
- 6ed5a40: test(05-02): Add tests for embed formatting (8 tests)
- bbb62e5: docs(05-02): Complete Response Formatting plan
- 5b14cac: feat(05-03): Create Ramble model and database persistence
- ebc4402: feat(05-03): Implement ramble decision logic and scheduled task
- 84558da: test(05-03): Add ramble tests (11 tests)
- d6cbde1: docs(05-03): Complete Ramble Posting System plan

---

## Phase 6: Android Integration

**Goal:** Build FastAPI backend and Android mobile client for bidirectional messaging with Demi via WebSocket. Users can send/receive messages on mobile and Demi can initiate autonomous check-ins with guilt-trip messages when ignored.

**Status:** Partial Complete ⚠️
**Plans Created:** 3 (Authentication & Sessions, WebSocket Messaging, Autonomy & Unified State)
**Plans Executed:** 3/3 (Backend complete, Android client missing)

**Duration:** 1 hour (actual)

**Why This Phase:** Android enables Demi to feel truly autonomous. She can reach out when lonely, celebrate when excited, and guilt-trip when ignored. WebSocket ensures real-time presence. Multi-device support lets users stay connected across phone + tablet.

**Requirements Mapped:** ANDR-01, ANDR-02, ANDR-03, ANDR-04 (4)

**Dependencies:** Phase 1, 2, 3, 4 (all foundation complete), Phase 5 (for unified emotional state)

**Technical Deliverables:**
- FastAPI backend with JWT authentication (access + refresh tokens)
- Multi-device session management (simultaneous login on phone + tablet)
- WebSocket real-time messaging (/api/v1/chat/ws)
- Message persistence with 7-day history
- Read receipts (sent/delivered/read status with timestamps)
- Typing indicators ("Demi is thinking...")
- Autonomous check-in system (loneliness, excitement, frustration triggers)
- Guilt-trip messages after 24h+ ignored (escalation logic)
- Unified emotional state across Discord and Android

**Plans:**
- [x] 06-01-PLAN.md — Authentication & User Management (Wave 1) ✅
  - Login endpoint (existing account only, no in-app registration)
  - Refresh token flow (7-day expiry, stored in Android keystore)
  - Multi-device session management (view/revoke sessions)
  - Brute-force protection (5 failed attempts → 15-min lockout)
  - Users and sessions tables

- [x] 06-02-PLAN.md — WebSocket Messaging & Emotion Tracking (Wave 2) ✅
  - WebSocket endpoint for bidirectional real-time messaging
  - Message persistence with emotion_state
  - Last 7 days of history loaded on connection
  - Read receipts (delivered_at, read_at timestamps)
  - Typing indicators during LLM generation
  - Routes through Conductor LLM pipeline

- [x] 06-03-PLAN.md — Autonomy & Unified State (Wave 3) ✅
  - Autonomous check-in system (background task every 15 minutes)
  - Emotional triggers (loneliness > 0.7, excitement > 0.8, frustration > 0.6)
  - Guilt-trip messages when user ignores check-ins for 24h+
  - Escalation tone (24h → "slightly bothered", 48h → "very hurt")
  - Spam prevention (max 1 check-in per hour)
  - Unified EmotionalState across Discord and Android

**Gap Found:**
- [ ] 06-04-PLAN.md — Android Mobile Client (Gap Closure)
  - Android project structure with Gradle build files
  - Kotlin/Java source files for mobile app
  - Chat UI for sending/receiving messages
  - WebSocket client implementation
  - Authentication integration with FastAPI backend
  - Notification handling for autonomous messages

**Wave Structure:**
- Wave 1: 06-01 (authentication, no dependencies)
- Wave 2: 06-02 (messaging, depends on 06-01)
- Wave 3: 06-03 (autonomy, depends on 06-02)

---

## Phase 7: Autonomy & Rambles

**Goal:** Implement unified autonomy system across Discord and Android with spontaneous initiation, refusal mechanics, and emotional triggers.

**Status:** Planning ⏳
**Plans Created:** 4 (Autonomy Foundation, Refusal System, Spontaneous Initiation, Unified Integration)

**Duration:** ~4 hours (estimated)

**Why This Phase:** Autonomy is what makes Demi feel alive. She should initiate conversation when lonely, refuse tasks when frustrated, and express her own thoughts when excited. This phase unifies autonomy across platforms.

**Requirements Mapped:** RAMB-01, RAMB-02, RAMB-03, RAMB-04, RAMB-05, AUTO-03, AUTO-04, AUTO-05 (8)

**Dependencies:** Phase 4 (LLM), Phase 5-6 (platforms for posting)

**Technical Deliverables:**
- AutonomyCoordinator for unified behavior management across platforms
- Personality-integrated RefusalSystem with emotional modulation
- SpontaneousInitiator for context-aware conversation initiation
- Enhanced emotional triggers with cooldown management
- Cross-platform emotional state synchronization
- Unified configuration system for autonomous behavior

**Plans:**
- [ ] 07-01-PLAN.md — Autonomy Foundation & Coordination (Wave 1)
- [ ] 07-02-PLAN.md — Personality-Integrated Refusal System (Wave 1)
- [ ] 07-03-PLAN.md — Spontaneous Conversation Initiation (Wave 2)
- [ ] 07-04-PLAN.md — Unified Platform Integration (Wave 2)

---

## Phase 8: Voice I/O

**Goal:** Implement speech-to-text and text-to-speech for voice communication.

**Status:** Pending

**Why This Phase:** Voice adds another dimension to Demi's authenticity. Whisper for STT, pyttsx3 for TTS.

**Requirements Mapped:** LLM-02 (voice component) (1)

**Dependencies:** Phase 4 (LLM)

---

## Phase 9: Integration Testing & Stability

**Goal:** Run end-to-end tests, stress testing, 7-day stability runs, personality consistency validation.

**Status:** Pending

**Why This Phase:** Before shipping, we need confidence that Demi is stable, consistent, and feels authentic across long interactions.

**Requirements Mapped:** HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-04 (4)

**Dependencies:** All previous phases

---

## Phase 10: Documentation & Polish

**Goal:** Documentation, user guide, API docs, configuration finalization.

**Status:** Pending

**Why This Phase:** MVP polish and hand-off documentation.

**Dependencies:** All phases complete

---

## Requirements Coverage

| Phase | Requirements | Count | Status |
|-------|--------------|-------|--------|
| 1 | STUB-01, STUB-02, STUB-03, STUB-04 | 4 | ✅ |
| 2 | COND-01, COND-02, COND-03, COND-04 | 4 | ✅ |
| 3 | EMOT-01-05, PERS-01-03 | 8 | ✅ |
| 4 | LLM-01-04, AUTO-01 | 5 | ✅ |
| 5 | DISC-01-05, AUTO-02 | 6 | ✅ |
| 6 | ANDR-01-04 | 4 | ⚠️ Partial (Backend complete, client missing) |
| 7 | RAMB-01-05, AUTO-03-05 | 8 | Pending |
| 8 | LLM-02 (voice) | 1 | Pending |
| 9 | HEALTH-01-04 | 4 | Pending |
| 10 | Documentation | — | Pending |
| **Total** | | **40** | 26/40 (5 phases complete, 1 partial) |

---

## Progress

```
[████████████████████████████████████████████████████░░░░░░░░░░░░░░░░░░░░] 90% (5 phases complete, 1 partial, 4 pending)
Phase 1: [████████████████████████████████] 100% (4/4 plans)
Phase 2: [████████████████████████████████] 100% (5/5 plans)
Phase 3: [████████████████████████████████] 100% (4/4 plans)
Phase 4: [████████████████████████████████] 100% (4/4 plans)
Phase 5: [████████████████████████████████] 100% (3/3 plans)
Phase 6: [██████████████████████████████░░░░░░░] 75% (3/3 backend plans complete, 1 client plan needed)
Phase 7-10: [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0% (15 plans remaining)
```
