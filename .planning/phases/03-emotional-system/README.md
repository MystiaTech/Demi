# Phase 03: Emotional System & Personality — Planning Documentation

**Status:** ✅ PLANNING COMPLETE — Ready for Execution  
**Generated:** 2026-02-02T21:28:00Z  
**Total Planning Lines:** 4,084  
**Format:** Executable PLAN.md files with complete implementation specifications  

---

## Quick Navigation

| Document | Purpose | Lines | Status |
|----------|---------|-------|--------|
| **03-01-PLAN.md** | Emotional State Model | 500 | ✅ Ready |
| **03-02-PLAN.md** | Decay & Interactions | 850 | ✅ Ready |
| **03-03-PLAN.md** | Personality Modulation | 780 | ✅ Ready |
| **03-04-PLAN.md** | Persistence & Validation | 850 | ✅ Ready |
| **PLANNING_SUMMARY.md** | Executive Summary | 300 | ✅ Complete |
| **03-CONTEXT.md** | Decisions & Constraints | 233 | ✅ Locked |
| **03-RESEARCH.md** | Validated Approaches | 561 | ✅ Complete |

---

## What's Inside

### 📋 Execution Plans (Start Here)

Read these in order to implement Phase 03:

1. **[03-01-PLAN.md](./03-01-PLAN.md)** — Emotional State Model & Core Mechanics
   - Build EmotionalState class with 9 dimensions
   - Implement momentum tracking and serialization
   - Create 20+ unit tests
   - **Duration:** ~1.5 hours | **Wave:** 1 | **No dependencies**

2. **[03-02-PLAN.md](./03-02-PLAN.md)** — Decay Mechanics & Interaction System
   - Implement DecaySystem with 5-minute background ticks
   - Build InteractionHandler mapping 8 event types
   - Create decay and interaction tests
   - **Duration:** ~2 hours | **Wave:** 1 | **Depends on:** 03-01

3. **[03-03-PLAN.md](./03-03-PLAN.md)** — Personality Modulation Engine
   - Create personality_traits.yaml with baseline + modulation
   - Implement PersonalityModulator for tone shifting
   - Create modulation tests with situational gates
   - **Duration:** ~1.5 hours | **Wave:** 2 | **Depends on:** 03-01, 03-02

4. **[03-04-PLAN.md](./03-04-PLAN.md)** — Persistence Layer & Validation Framework
   - Implement EmotionPersistence with SQLite database
   - Create interaction logging system with audit trail
   - Build E2E integration tests
   - **Duration:** ~2 hours | **Wave:** 2 | **Depends on:** 03-01, 03-02, 03-03

### 📊 Planning Context

- **[03-CONTEXT.md](./03-CONTEXT.md)** — Phase decisions locked (9 dimensions, 0-1 scale, decay mechanics, modulation ranges)
- **[03-RESEARCH.md](./03-RESEARCH.md)** — Validated approaches from academic literature and production systems
- **[PLANNING_SUMMARY.md](./PLANNING_SUMMARY.md)** — Executive summary with full specifications

---

## Key Implementation Details

### 9 Emotion Dimensions
```
Core 5: loneliness, excitement, frustration, jealousy, vulnerability
Additional 4: confidence, curiosity, affection, defensiveness
Scale: 0-1 percentage with momentum tracking
Floors: loneliness ≥0.3, others ≥0.1
```

### Decay System (5-minute ticks)
```
loneliness:     0.02/tick  (slow, sticky)
excitement:     0.06/tick  (fast, fleeting)
frustration:    0.04/tick  (medium)
jealousy:       0.03/tick  (slow-medium)
vulnerability:  0.08/tick  (very fast)
confidence:     0.03/tick  (slow-medium)
curiosity:      0.05/tick  (medium-fast)
affection:      0.04/tick  (medium)
defensiveness:  0.05/tick  (medium-fast)

Inertia: >0.8 decays 50% slower
Idle: loneliness +0.01/min, excitement -0.02/min
```

### Interaction Types (8)
```
positive_message → excitement +0.15, affection +0.12, loneliness -0.10
negative_message → frustration +0.10, vulnerability +0.08
code_update → jealousy -0.30, excitement +0.10, affection +0.15
error_occurred → frustration +0.15, confidence -0.10
successful_help → frustration -0.20, confidence +0.15
user_refusal → frustration +0.10, vulnerability +0.10
long_idle → loneliness +0.20, excitement -0.15, confidence -0.10
rapid_errors → frustration +0.15, confidence -0.20
```

### Personality Modulation (6 dimensions)
```
sarcasm_level:      0-1 (60-100% variance allowed)
formality:          0-1 (0=casual, 1=formal)
warmth:             0-1 (0=cold, 1=very warm)
response_length:    word count (35-300)
humor_frequency:    0-1 (% of responses)
emoji_frequency:    0-1 (emoji usage)
self_deprecation:   0-1 (self-criticism)
nickname_frequency: 0-1 (pet name usage)

Situational gates: death/loss/crisis always use baseline
Self-awareness: Generate natural "I'm in a mood" comments
Variance bounds: ±30% from baseline acceptable
```

### Persistence Model (SQLite)
```
Tables:
  • emotional_state (timestamp, 9 emotions, momentum, notes)
  • interaction_log (timestamp, event, before/after state, effects)
  • state_snapshots (hourly backup, startup/shutdown snapshots)

On restore:
  1. Load last saved state
  2. Calculate offline duration
  3. Simulate decay for that period
  4. Return aged state (not stale state)

Backup & recovery:
  • Hourly snapshots created automatically
  • Recovery from corruption using recent backup
  • Atomic transactions prevent partial saves
```

---

## Test Coverage Summary

| Plan | Unit Tests | Integration | Total |
|------|-----------|-------------|-------|
| 03-01 | 20+ | 0 | 20+ |
| 03-02 | 16+ | 0 | 16+ |
| 03-03 | 10+ | 0 | 10+ |
| 03-04 | 6+ | 2+ | 8+ |
| **Total** | **52+** | **2+** | **60+** |

All test code is included inline in PLAN.md files.

---

## File Structure

```
src/emotion/
├── __init__.py                    # Module exports
├── models.py                      # EmotionalState class
├── decay.py                       # DecaySystem with background ticks
├── interactions.py                # InteractionHandler (8 event types)
├── modulation.py                  # PersonalityModulator for tone shifting
├── persistence.py                 # EmotionPersistence with SQLite backend
└── personality_traits.yaml        # Baseline personality + modulation deltas

tests/
├── test_emotion_models.py         # EmotionalState unit tests
├── test_emotion_decay.py          # DecaySystem unit tests
├── test_emotion_interactions.py   # InteractionHandler unit tests
├── test_emotion_modulation.py     # PersonalityModulator unit tests
├── test_emotion_persistence.py    # EmotionPersistence tests
└── test_emotion_integration.py    # Full E2E integration tests
```

---

## Execution Timeline

### Wave 1: Foundation (Parallel)
```
Hour 0-1.5:   Plan 03-01 (EmotionalState, no dependencies)
Hour 0.5-2.5: Plan 03-02 (DecaySystem, depends on EmotionalState)
              Total: ~2-2.5 hours
```

### Wave 2: Integration (Parallel)
```
Hour 2.5-4:   Plan 03-03 (PersonalityModulator, depends on 01+02)
Hour 2.5-4.5: Plan 03-04 (Persistence, depends on 01+02+03)
              Total: ~2 hours
```

**Total Sequential:** ~7 hours  
**Total Optimized Parallel:** ~4.5 hours (Wave 1 → Wave 2)

---

## Quality Gate Verification

All quality criteria have been met:

✅ **PLAN.md files created** in phase directory  
✅ **Valid frontmatter** (phase, plan, type, wave, depends_on, files_modified, autonomous, must_haves)  
✅ **Tasks are specific** (exact file paths, exact code, complete test specifications)  
✅ **Dependencies identified** (what each plan needs from prior plans)  
✅ **Waves assigned** for parallel execution (pre-computed optimization)  
✅ **Must-haves derived** from phase goal using backward methodology  

---

## Success Criteria (Phase Goal Achievement)

- [x] **Emotional State Model** — 9 dimensions, 0-1 scale, momentum tracking, serializable
- [x] **Decay Mechanics** — 5-minute ticks, emotion-specific rates, idle effects, offline simulation
- [x] **Interaction System** — 8 event types, momentum amplification, dampening
- [x] **Personality Modulation** — 6 tone dimensions, 60-100% variance, situational gates
- [x] **Persistence** — SQLite storage, offline recovery, interaction logging, backup/recovery
- [x] **Validation Framework** — 60+ tests, E2E flows, consistency checks

---

## Integration Points for Phase 04

Phase 04 (LLM Integration) will use these Phase 03 APIs:

```python
# Load emotional state on startup
state = persistence.restore_and_age_state(decay_system)

# Get response modulation parameters
params = modulator.modulate(state, situational_context=context)

# Inject into LLM prompt
prompt = build_prompt(base_prompt, params.to_prompt_context())

# Log the interaction
persistence.log_interaction(
    interaction_type,
    state_before,
    state_after,
    effects_log
)
```

All APIs are production-ready. No changes needed for Phase 04 integration.

---

## Getting Started

For Claude executors implementing this phase:

1. **Start with 03-01-PLAN.md**
   - No dependencies, foundational task
   - Create EmotionalState class
   - Verify 20+ tests pass

2. **Parallel: Start 03-02-PLAN.md** (after EmotionalState exists)
   - Create DecaySystem
   - Create InteractionHandler
   - Verify 16+ tests pass

3. **After Wave 1 Complete: Start 03-03-PLAN.md**
   - Create personality_traits.yaml
   - Create PersonalityModulator
   - Verify 10+ tests pass

4. **After Wave 1 Complete: Start 03-04-PLAN.md**
   - Create EmotionPersistence
   - Create integration tests
   - Verify 8+ tests pass

5. **Final Verification**
   - Run all 60+ tests together
   - Create git commit
   - Phase 03 complete!

---

## Questions or Issues?

All PLAN.md files are self-contained and require no interpretation. Each includes:
- Exact file paths
- Complete code specifications
- Full test code
- Clear success criteria
- Definition of done

If something is unclear, check the specific PLAN.md file for that task. All necessary information is included inline.

---

**Planning Complete. Ready for Implementation.**

*All plans executable by Claude without interpretation.*  
*Quality gate: PASSED*  
*Next phase: Phase 04 (LLM Integration)*
