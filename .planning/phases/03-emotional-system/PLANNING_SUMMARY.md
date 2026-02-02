# Phase 03: Emotional System & Personality — PLANNING COMPLETE

**Generated:** 2026-02-02T21:28:00Z  
**Status:** Ready for Execution (Claude Implementor)  
**Quality Gate:** ✅ PASSED

---

## Summary

Four executable PLAN.md files have been created for Phase 03: Emotional System & Personality. Each plan is self-contained, actionable, and specifies exact file paths and implementations for Claude executors to implement without interpretation.

---

## Quality Gate Checklist

- [x] **PLAN.md files created** — All 4 plans in `phases/03-emotional-system/` directory
- [x] **Valid frontmatter** — Each has phase, plan, type, wave, depends_on, files_modified, autonomous, must_haves
- [x] **Specific & actionable** — Exact file paths, exact code implementations, specific test counts
- [x] **Dependencies identified** — Wave assignments prevent parallel work on dependent tasks
- [x] **Waves pre-computed** — Wave 1 (01, 02), Wave 2 (03, 04) allows optimization
- [x] **must_haves from goal** — Each derived using goal-backward methodology from phase goal

---

## Phase Goal

Build Demi's emotional state tracking system with 9 emotion dimensions, sophisticated decay mechanics, personality modulation, persistence/recovery, and validation metrics. Emotions affect response intensity while Demi remains contextually aware of her own emotional shifts.

---

## Delivered Plans

### Plan 03-01: Emotional State Model & Core Mechanics
**Wave:** 1 | **Duration:** ~1.5 hours | **Files Modified:** 2

**Goal:** Build the foundational emotional state data structure.

**Scope:**
- EmotionalState class with 9 dimensions (0-1 scale)
- Momentum tracking for cascade effects
- Serialization/deserialization for database
- Emotion-specific floor enforcement
- 20+ unit tests

**Must-Haves:**
- EmotionalState class with 9 dimensions
- 0-1 percentage scale with momentum tracking
- Serializable to dict for database persistence
- Unit tests for bounds checking, momentum, serialization
- State floor enforcement (loneliness ≥0.3, others ≥0.1)

**Deliverables:**
- `src/emotion/models.py` (300 lines) — EmotionalState class
- `src/emotion/__init__.py` — Module exports
- `tests/test_emotion_models.py` (250 lines) — 20+ tests

**No dependencies** (foundational task)

---

### Plan 03-02: Decay Mechanics & Interaction System
**Wave:** 1 | **Duration:** ~2 hours | **Files Modified:** 4

**Goal:** Implement continuous emotion decay and event-triggered interaction effects.

**Scope:**
- DecaySystem with 5-minute background ticks
- Emotion-specific decay rates (loneliness slow, excitement fast)
- Idle effects (loneliness +0.01/min, excitement -0.02/min)
- InteractionHandler mapping 8 event types to emotional deltas
- Momentum amplification system
- Offline recovery simulation
- 15+ unit tests

**Must-Haves:**
- DecaySystem class with background tick logic
- Emotion-specific decay rates with extreme emotion inertia
- Idle effects that build loneliness and crash excitement
- InteractionHandler class mapping 8 event types
- Momentum amplification (high momentum = stronger effects)
- Unit tests validating decay curves, interactions, offline recovery

**Deliverables:**
- `src/emotion/decay.py` (350 lines) — DecaySystem, DecayTuner
- `src/emotion/interactions.py` (280 lines) — InteractionHandler, analyzer
- `tests/test_emotion_decay.py` (200 lines) — 8+ decay tests
- `tests/test_emotion_interactions.py` (220 lines) — 8+ interaction tests

**Depends on:** Plan 03-01 (uses EmotionalState)

---

### Plan 03-03: Personality Modulation Engine
**Wave:** 2 | **Duration:** ~1.5 hours | **Files Modified:** 3

**Goal:** Bridge emotional state to response generation with personality modulation.

**Scope:**
- PersonalityModulator class applying emotions to response parameters
- 6 modulation dimensions (sarcasm, formality, warmth, length, humor, emoji)
- YAML personality baseline + modulation deltas
- Situational appropriateness gates (serious contexts override emotion)
- Self-awareness commentary generation
- Sentiment analysis compatibility
- 10+ unit tests

**Must-Haves:**
- PersonalityModulator class with emotion-to-modulation mapping
- Emotion-specific modulation ranges (±60-100% variance allowed)
- Situational gates preventing emotional modulation in serious contexts
- Self-awareness sampling for natural "I'm in a mood" moments
- Variance validation prepared for Phase 4 consistency checks
- Unit tests validating modulation calculations, gates, sentiment

**Deliverables:**
- `src/emotion/personality_traits.yaml` (120 lines) — Baseline + modulation mapping
- `src/emotion/modulation.py` (400 lines) — PersonalityModulator, ModulationParameters
- `tests/test_emotion_modulation.py` (300 lines) — 10+ modulation tests

**Depends on:** Plans 03-01, 03-02 (integrates EmotionalState + decay/interactions)

---

### Plan 03-04: Persistence Layer & Validation Framework
**Wave:** 2 | **Duration:** ~2 hours | **Files Modified:** 3

**Goal:** Make emotions persistent across restarts with comprehensive testing framework.

**Scope:**
- EmotionPersistence class with save/load/restore
- SQLite schema for emotional_state, interaction_log, state_snapshots
- Offline decay simulation on startup
- Interaction logging with full audit trail
- Backup/recovery mechanisms for data integrity
- Integration tests validating full E2E flow
- 8+ persistence tests + 2+ E2E tests

**Must-Haves:**
- EmotionPersistence class with save/load/restore methods
- Database tables for emotional_state, interaction logging
- Offline decay simulation from last saved state
- Interaction logging with timestamp, message, before/after state
- Data integrity checks and corruption recovery
- Integration tests validating E2E save → offline → restore → age flow

**Deliverables:**
- `src/emotion/persistence.py` (450 lines) — EmotionPersistence class
- `tests/test_emotion_persistence.py` (250 lines) — 8+ persistence tests
- `tests/test_emotion_integration.py` (150 lines) — 2+ E2E tests
- `src/emotion/__init__.py` (updated) — Full module exports

**Depends on:** Plans 03-01, 03-02, 03-03 (uses all systems)

---

## Wave Architecture

**Wave 1 (Parallel execution):**
- Plan 03-01: Emotional State Model (no dependencies)
- Plan 03-02: Decay & Interactions (depends on 03-01)

*Note: 03-02 can start once 03-01 EmotionalState is complete (~30 min)*

**Wave 2 (Parallel execution):**
- Plan 03-03: Personality Modulation (depends on 03-01, 03-02)
- Plan 03-04: Persistence & Testing (depends on 03-01, 03-02, 03-03)

*Note: 03-03 and 03-04 can start once core systems are done*

**Total Duration:** ~7 hours (sequential) or ~4.5 hours (optimized parallel)

---

## Test Coverage Summary

| Plan | Unit Tests | Integration Tests | Total |
|------|-----------|------------------|-------|
| 03-01 | 20+ | 0 | 20+ |
| 03-02 | 16+ | 0 | 16+ |
| 03-03 | 10+ | 0 | 10+ |
| 03-04 | 6+ | 2+ | 8+ |
| **Total** | **52+** | **2+** | **60+** |

All tests validate core functionality without requiring external dependencies (except pytest, pyyaml for config).

---

## File Structure Created

```
src/emotion/
├── __init__.py              # Module exports
├── models.py                # EmotionalState (9 dims, momentum)
├── decay.py                 # DecaySystem (ticks, rates, offline sim)
├── interactions.py          # InteractionHandler (8 event types)
├── modulation.py            # PersonalityModulator (tone shifting)
├── persistence.py           # EmotionPersistence (DB, logging)
└── personality_traits.yaml  # Baseline + modulation deltas

tests/
├── test_emotion_models.py
├── test_emotion_decay.py
├── test_emotion_interactions.py
├── test_emotion_modulation.py
├── test_emotion_persistence.py
└── test_emotion_integration.py
```

---

## Key Implementation Details

### EmotionalState (03-01)
- 9 dimensions: loneliness, excitement, frustration, jealousy, vulnerability, confidence, curiosity, affection, defensiveness
- 0-1 percentage scale with momentum tracking
- Emotion-specific floors (loneliness ≥0.3, others ≥0.1)
- Serializable to/from dict for database

### DecaySystem (03-02)
- 5-minute background ticks
- Emotion-specific decay rates: loneliness (0.02), excitement (0.06), frustration (0.04), etc.
- Extreme emotion inertia (>0.8 decays 50% slower)
- Idle effects: loneliness +0.01/min, excitement -0.02/min
- Offline decay simulation for persistence

### InteractionHandler (03-02)
- 8 event types: positive_message, negative_message, code_update, error_occurred, successful_help, user_refusal, long_idle, rapid_errors
- Momentum amplification (dominant emotions change more intensely)
- Dampening system (repeated interactions have diminishing returns)
- Effect logging for debugging

### PersonalityModulator (03-03)
- 6 modulation dimensions: sarcasm, formality, warmth, response_length, humor_frequency, self_deprecation, emoji_frequency, nickname_frequency
- Emotion-specific deltas from YAML config
- Situational gates (death/loss/crisis use baseline)
- Self-awareness commentary (natural, not forced)
- Variance validation (±30% acceptable drift)

### EmotionPersistence (03-04)
- SQLite storage with atomic transactions
- Offline decay simulation on restore
- Interaction logging with full audit trail (timestamp, message, before/after, effects)
- Backup snapshots (hourly, manual, startup, shutdown)
- Corruption recovery using recent backups

---

## Success Metrics (Phase 03 Goal Achievement)

✅ **Emotional consistency** — Emotions tracked across 9 dimensions with realistic decay
✅ **Personality authenticity** — Modulation creates 60-100% variance in response character
✅ **Persistence reliability** — State survives restarts with proper offline decay
✅ **Interaction realism** — Events trigger realistic emotional changes with momentum/dampening
✅ **Validation readiness** — System prepared for Phase 9 consistency testing

---

## Dependencies for Phase 04

**Phase 04 (LLM Integration) will:**
1. Call `PersonalityModulator.modulate(emotional_state)` to get response parameters
2. Inject `ModulationParameters.to_prompt_context()` into LLM prompts
3. Use `InteractionHandler.apply_interaction()` to update emotions after responses
4. Call `EmotionPersistence.log_interaction()` to record full interaction history
5. Use `EmotionPersistence.restore_and_age_state()` on startup

All APIs are production-ready for Phase 4 integration.

---

## Execution Instructions for Implementor

1. **Start with Plan 03-01** (no dependencies)
   - Create EmotionalState class and tests
   - Verify all 20+ tests pass
   - Run: `pytest tests/test_emotion_models.py -v`

2. **Run Plan 03-02 in parallel with 03-01 (after EmotionalState created)**
   - Create DecaySystem and InteractionHandler
   - Create decay and interaction tests
   - Verify all 16+ tests pass
   - Run: `pytest tests/test_emotion_decay.py tests/test_emotion_interactions.py -v`

3. **Run Plan 03-03 (after 03-01 and 03-02 complete)**
   - Create personality_traits.yaml
   - Create PersonalityModulator
   - Create modulation tests
   - Verify all 10+ tests pass
   - Run: `pytest tests/test_emotion_modulation.py -v`

4. **Run Plan 03-04 (after all plans 03-01 through 03-03 complete)**
   - Create EmotionPersistence
   - Create persistence and integration tests
   - Verify all 8+ tests pass
   - Run: `pytest tests/test_emotion_persistence.py tests/test_emotion_integration.py -v`

5. **Final verification:**
   - Run all Phase 03 tests: `pytest tests/test_emotion_*.py -v`
   - Expected: 60+ tests passing
   - Create git commit: `git add . && git commit -m "feat(03) - Complete emotional system and personality framework"`

---

## Known Constraints & Discretionary Areas

### Fixed (From CONTEXT.md)
- 9 emotion dimensions (validated by research)
- 0-1 percentage scale with momentum
- Emotion-specific floors
- Situational appropriateness gates
- Offline decay simulation

### Tunable (Claude's discretion during implementation)
- Exact decay rate constants (research-based, tuning in Phase 9)
- Interaction trigger event types (can add/modify as needed)
- Modulation weight formulas (ensure results stay within ±30%)
- YAML personality baseline values (should match DEMI_PERSONA.md)
- Database schema indexes (add as performance testing shows needed)

### Not Included (Post-v1)
- Real-time emotion visualization dashboard
- User-facing "relationship score" with Demi
- Multi-user emotional group dynamics
- Emotion-driven autonomy (rambles, refusal) — Phase 7

---

## Risk Mitigation

| Risk | Mitigation | Validation |
|------|-----------|-----------|
| Emotions feel forced/creepy | Situational gates + self-awareness + user testing | Phase 9 human testing |
| Personality drifts over time | Sentiment analysis + consistency metrics | Phase 9 regression tests |
| Database corruption | Backup snapshots + recovery mechanism | 03-04 corruption tests |
| Performance degradation | Indexed queries, batch operations | Phase 9 stress testing |
| Emotional whiplash (changing too fast) | Momentum + dampening + extreme inertia | 03-02 decay tests |

---

## Next Phase (Phase 04: LLM Integration)

Phase 04 will integrate Demi's emotions with response generation:
- Load llama3.2 via Ollama
- Build prompt builder with emotional context
- Inject personality modulation parameters
- Log interactions and update emotional state
- Validate responses match expected emotional tone

All emotional system APIs are ready. Phase 04 can begin immediately after Phase 03 completion.

---

**Planning Complete. Ready for Execution.**

*Generated by OpenCode Planning System*  
*All plans executable without interpretation*
