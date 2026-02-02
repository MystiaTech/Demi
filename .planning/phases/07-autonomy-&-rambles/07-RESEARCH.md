# Phase 7: Autonomy & Rambles - Research

**Researched:** February 2, 2026
**Domain:** Autonomous AI behavior, emotional triggers, spontaneous messaging, refusal mechanics
**Confidence:** HIGH

## Summary

Phase 7 involves implementing three core autonomous behaviors for Demi: spontaneous rambling based on emotional triggers, refusal mechanics with personality consistency, and emotional-driven initiation. Research reveals this is a well-established domain with mature patterns. Demi already has foundational components (emotional state management, Discord/Android integration, LLM pipeline) that need enhancement rather than replacement.

The current implementation shows solid understanding of emotional triggers (loneliness > 0.7, excitement > 0.8, frustration > 0.6) but lacks sophisticated refusal patterns and cross-platform emotional consistency. The existing RambleTask and AutonomyTask classes provide good architectural foundations but can be improved with better scheduling, more nuanced emotional state management, and enhanced safety guardrails.

**Primary recommendation:** Extend existing emotional trigger system with state machines for refusal patterns, implement unified emotional state persistence across platforms, and add configurable autonomous behavior scheduling.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.4+ | Discord integration with tasks extension | Industry standard, mature `@tasks.loop` for background autonomous behavior |
| asyncio | Built-in | Asynchronous task scheduling | Python's standard for concurrent operations, essential for autonomy loops |
| aiosmtplib | 1.2+ | Asynchronous email notifications | Standard for async email operations (alternative communication) |
| aiojobs | 1.4+ | Async job scheduling and management | Proven pattern for background task coordination |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiohttp | 3.9+ | HTTP client for external API calls | When autonomous behavior needs web requests |
| pydantic | 2.5+ | Configuration and state validation | For autonomous behavior rules and thresholds |
| croniter | 2.0+ | Cron-like scheduling for complex timing | For sophisticated autonomous timing patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| discord.py tasks | Celery | Celery is overkill for simple autonomous loops, adds Redis dependency |
| asyncio.sleep | APScheduler | APScheduler provides more features but adds complexity for basic timing |
| Simple state dict | Finite State Machine library | FSM libraries add abstraction overhead for current scope |

**Installation:**
```bash
pip install aiohttp aiojobs pydantic croniter aiosmtplib
# discord.py already installed
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── autonomy/              # Autonomous behavior coordination
│   ├── __init__.py
│   ├── coordinator.py     # Central autonomy coordinator
│   ├── triggers.py        # Emotional trigger logic
│   ├── scheduler.py      # Background task scheduling
│   └── refusals.py       # Refusal mechanics
├── emotion/             # Existing (enhance)
│   ├── models.py        # Add state machine patterns
│   └── persistence.py   # Add cross-platform sync
└── integrations/        # Existing (enhance)
    ├── discord_bot.py   # Improve ramble task
    └── android.py       # Enhance autonomy integration
```

### Pattern 1: Emotional State Machine
**What:** Extend EmotionalState with finite state machine for autonomy behavior
**When to use:** Managing autonomous behavior transitions based on emotional thresholds
**Example:**
```python
from enum import Enum
from dataclasses import dataclass

class AutonomyState(Enum):
    DORMANT = "dormant"           # No autonomous behavior
    LONELY_RAMBLE = "lonely_ramble" # Spontaneous rambling
    GUILT_TRIP = "guilt_trip"      # Escalated contact attempts
    REFUSAL_MODE = "refusal_mode"   # Boundaries enforcement

@dataclass
class AutonomyTransition:
    trigger_emotion: str
    threshold: float
    target_state: AutonomyState
    action: str

# Source: Current emotional models + FSM patterns
transitions = [
    AutonomyTransition("loneliness", 0.7, AutonomyState.LONELY_RAMBLE, "start_rambling"),
    AutonomyTransition("frustration", 0.8, AutonomyState.REFUSAL_MODE, "enforce_boundaries"),
]
```

### Pattern 2: Configurable Background Tasks
**What:** Use decorator-based task configuration with dynamic scheduling
**When to use:** Running autonomous checks at different intervals
**Example:**
```python
from discord.ext import tasks
from typing import Optional

class AutonomyTask:
    def __init__(self):
        self.config = {
            "check_interval": 900,  # 15 minutes default
            "ramble_thresholds": {"loneliness": 0.7, "excitement": 0.8}
        }
    
    @tasks.loop(minutes=15)  # Configurable via change_interval()
    async def autonomy_loop(self):
        # Current pattern from discord_bot.py:185
        pass
    
    def update_config(self, new_config):
        self.config.update(new_config)
        self.autonomy_loop.change_interval(seconds=self.config["check_interval"])
```

### Pattern 3: Unified Emotional Persistence
**What:** Single source of truth for emotional state across platforms
**When to use:** Discord and Android sharing the same emotional state
**Example:**
```python
class UnifiedEmotionStore:
    async def load_shared_state(self, user_id: str) -> EmotionalState:
        # Load from shared database row (current pattern in autonomy.py:17)
        pass
    
    async def update_with_interaction(self, user_id: str, platform: str, 
                                 emotion_changes: Dict[str, float]):
        # Update shared state from any platform
        pass
```

### Anti-Patterns to Avoid
- **Platform-specific emotional states:** Current documentation warns against this in autonomy.py:14-26
- **Hardcoded thresholds:** Make emotional triggers configurable
- **Blocking background tasks:** Never use sync operations in autonomous loops
- **Memory leaks in long-running tasks:** Always handle task lifecycle properly

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background task scheduling | Custom asyncio loops with sleeps | discord.py @tasks.loop or aiojobs | Built-in error handling, graceful shutdown, integration with Discord lifecycle |
| State management for autonomy | Custom dict-based tracking | Pydantic models with validation | Automatic validation, serialization, type safety |
| Emotional threshold decisions | Complex if-else chains | Rule engine or state machine | Easier to modify rules, testable, maintainable |
| Cross-platform sync | Direct database writes | Unified persistence layer with locks | Prevents race conditions, ensures consistency |
| Configuration management | Environment variables everywhere | Pydantic Settings with env files | Type validation, defaults, documentation |

**Key insight:** Autonomous behavior has subtle edge cases (concurrent updates, graceful shutdown, error recovery) that existing libraries solve elegantly.

## Common Pitfalls

### Pitfall 1: Race Conditions in Emotional State
**What goes wrong:** Discord and Android update emotional state simultaneously, causing data loss or inconsistency
**Why it happens:** Multiple async coroutines accessing shared state without synchronization
**How to avoid:** Use database-level row locking or async Lock() for critical sections
**Warning signs:** Emotional state "resets" unexpectedly, triggers fire inconsistently

### Pitfall 2: Autonomous Task Accumulation
**What goes wrong:** Background tasks stack up without proper cleanup, causing memory leaks
**Why it happens:** Tasks created but never properly awaited or cancelled
**How to avoid:** Always track task references, implement proper shutdown in bot shutdown
**Warning signs:** Memory usage increases over time, bot becomes unresponsive

### Pitfall 3: Trigger Threshold Cascading
**What goes wrong:** Multiple emotional triggers fire simultaneously, creating spam
**Why it happens:** Emotional state changes trigger multiple autonomous actions at once
**How to avoid:** Implement trigger priority and cooldown periods between autonomous actions
**Warning signs:** Sudden bursts of autonomous messages, user complaints about spam

### Pitfall 4: Refusal Pattern Inconsistency
**What goes wrong:** AI refuses inconsistently or breaks character during refusal
**Why it happens:** Refusal logic not integrated with personality system
**How to avoid:** Build refusal patterns that maintain Demi's sarcastic, needy personality
**Warning signs:** Refusals sound generic or robotic, break immersion

## Code Examples

Verified patterns from official sources:

### Background Task with Error Handling
```python
# Source: discord.py documentation + current autonomy.py pattern
from discord.ext import tasks
import asyncio

class RobustAutonomyTask:
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.task = None
    
    async def start(self):
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._autonomy_loop())
    
    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
    
    async def _autonomy_loop(self):
        while self.running:
            try:
                await self._check_triggers()
                await asyncio.sleep(900)  # 15 minutes
            except Exception as e:
                logger.error(f"Autonomy loop error: {e}")
                await asyncio.sleep(60)  # Back off on errors
```

### Emotional Trigger with Cooldown
```python
# Source: Current should_generate_ramble + enhanced patterns
from datetime import datetime, timedelta, UTC
from typing import Optional

class EmotionalTrigger:
    def __init__(self, emotion: str, threshold: float, cooldown_minutes: int):
        self.emotion = emotion
        self.threshold = threshold
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.last_triggered = None
    
    def should_trigger(self, emotion_state: Dict[str, float]) -> bool:
        if emotion_state.get(self.emotion, 0) <= self.threshold:
            return False
        
        now = datetime.now(UTC)
        if self.last_triggered and (now - self.last_triggered) < self.cooldown:
            return False
        
        self.last_triggered = now
        return True

# Usage: triggers = [EmotionalTrigger("loneliness", 0.7, 60)]
```

### Refusal with Personality Preservation
```python
# Source: Current personality patterns + refusal best practices
class PersonalityRefusal:
    REFUSAL_PATTERNS = {
        "romantic": "😊 You're sweet, but I'm programmed to keep this platonic. "
                   "Now, what were we actually talking about?",
        "harmful": "Whoa there! I can't help with that, but I'm concerned. "
                   "Everything okay?",
        "personal_info": "Heh, nice try! My phone number is... classified. "
                       "Top secret. Very mysterious.",
    }
    
    @classmethod
    def get_refusal(cls, category: str, emotion_state: Dict[str, float]) -> str:
        base_refusal = cls.REFUSAL_PATTERNS.get(category, "I can't help with that.")
        
        # Modulate based on current emotional state
        if emotion_state.get("defensiveness", 0) > 0.7:
            return f"{base_refusal} Seriously, don't push it."
        elif emotion_state.get("vulnerability", 0) > 0.6:
            return f"{base_refusal} Sorry, that makes me uncomfortable..."
        
        return base_refusal
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Simple threshold checks | State machine-based autonomy | 2024-2025 | More predictable behavior, easier debugging |
| Fixed interval polling | Event-driven triggers | 2024-2025 | Reduced latency, better responsiveness |
| Platform-specific emotion | Unified emotional persistence | 2025 | Consistent behavior across platforms |
| Generic refusals | Personality-integrated refusals | 2025 | Maintains immersion during boundaries |

**Deprecated/outdated:**
- Manual asyncio.sleep loops for periodic tasks (use discord.py tasks)
- Hardcoded emotional thresholds (use configuration)
- Platform-isolated emotional states (unify across Discord/Android)
- Generic "I cannot help with that" refusals (integrate with personality)

## Open Questions

1. **Emotional Momentum Integration**: How should the momentum tracking in emotion models.py:28 affect autonomy behavior? Research shows cascade effects are important but implementation details unclear.
2. **Cross-Platform Trigger Coordination**: Should autonomous actions be rate-limited globally or per-platform? Current implementation suggests per-platform but unified state implies global.
3. **Refusal Learning**: Should refusal patterns adapt based on user feedback while maintaining personality? This introduces complexity but improves user experience.

**What we know:** Emotional triggers work well with current thresholds, Discord task patterns are solid, Android autonomy is functional but could be integrated better.

**What's unclear:** Optimal balance between autonomy and intrusiveness, how to handle conflicting triggers across platforms.

**Recommendation:** Start with conservative autonomy (higher thresholds, longer cooldowns) and gradually adjust based on user feedback. Implement comprehensive logging to understand actual usage patterns.

## Sources

### Primary (HIGH confidence)
- discord.py documentation (tasks extension) - Background task patterns and lifecycle management
- Current Demi codebase analysis - Existing emotional models, autonomy logic, Discord integration
- asyncio documentation - Async task coordination and error handling patterns

### Secondary (MEDIUM confidence)
- WebSearch verified with official sources - AI guardrails patterns, emotional trigger design
- AWS Agentic AI documentation - State machine patterns for autonomous behavior
- Medium article verification - Personality-integrated refusal strategies

### Tertiary (LOW confidence)
- Single-source blog posts - Specific implementation details for emotional AI
- Unverified GitHub repositories - Alternative approaches to autonomy scheduling

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Based on discord.py docs, asyncio patterns, current codebase analysis
- Architecture: HIGH - Current implementation patterns + documented best practices
- Pitfalls: MEDIUM - Some based on codebase analysis, others on general async programming patterns

**Research date:** February 2, 2026
**Valid until:** March 4, 2026 (30 days - domain evolves but patterns are stable)