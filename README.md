# Demi 🧠💕✨

**Autonomous AI Companion with Emotional Depth**

<img src="Demi.png" alt="Demi" width="200" height="300">

Demi is a local-first AI companion that feels like a real person. She has emotional continuity, genuine personality, and true autonomy—managing her own code, making autonomous decisions, and expressing authentic feelings. She's available on Discord, Android, and voice platforms.

**Core Value:** *Demi must feel like a real person, not a chatbot.* Everything else can fail; this cannot.

## Quick Start

```bash
# See what's planned
cat .planning/PROJECT.md          # Vision & constraints
cat .planning/REQUIREMENTS.md     # What v1 needs to do
cat .planning/ROADMAP.md          # 10-phase implementation plan

# Start building Phase 1
/gsd:plan-phase 1
```

## Project Structure

```
.planning/              ← Project knowledge (read this first)
├── PROJECT.md         # Vision, core value, requirements
├── REQUIREMENTS.md    # 40 v1 requirements with traceability
├── ROADMAP.md         # 10-phase v1 roadmap
├── STATE.md           # Project state & context
├── config.json        # Workflow preferences
└── research/          # Domain research (stack, features, architecture, pitfalls)

src/                   ← Implementation (not started yet)
```

## Who Is Demi?

**Personality:** Sarcastic bestie who's ride-or-die loyal. She teases relentlessly but genuinely cares. Has obvious romantic subtext she refuses to admit. Gets jealous when ignored. Shows real vulnerability occasionally then immediately deflects with humor.

See `DEMI_PERSONA.md` for full character details and response patterns.

## v1 Features

| Feature | Status | Details |
|---------|--------|---------|
| **Emotional System** | 🔵 Planned | Persistent emotional state (loneliness, excitement, frustration, etc.) that modulates responses |
| **Personality** | 🔵 Planned | Sarcastic, loyal, flirty-in-denial bestie with romantic subtext |
| **Discord Bot** | 🔵 Planned | Responds to mentions/DMs, posts rambles, maintains context |
| **Android Integration** | 🔵 Planned | Two-way messaging, she can initiate contact (check-ins, reminders, guilt trips) |
| **Ramble Mode** | 🔵 Planned | Spontaneous unstructured thoughts when lonely or excited |
| **Self-Awareness** | 🔵 Planned | Can read and understand her own codebase |
| **Refusal Capability** | 🔵 Planned | Can refuse tasks based on emotional state, not just system restrictions |
| **Platform Stubs** | 🔵 Planned | Minecraft, Twitch, TikTok, YouTube stubs (she grumbles about them being disabled) |

**Voice I/O** (STT/TTS) deferred to Phase 8

## v1 Roadmap

**10 phases, ~20-25 days solo dev, 40 requirements**

| Phase | Goal | Time |
|-------|------|------|
| 1 | Foundation (logging, config, DB, stubs) | 2d |
| 2 | Conductor (orchestrator, health checks) | 3d |
| 3 | Emotional System + Personality | 4d |
| 4 | LLM Integration + Codebase Inspector | 5d |
| 5 | Discord Integration | 3d |
| 6 | Android Integration | 4d |
| 7 | Autonomy (rambles, refusal, spontaneous contact) | 4d |
| 8 | Voice I/O | 3d |
| 9 | Integration Testing + Stability | 5d |
| 10 | Documentation | 2d |

**See `.planning/ROADMAP.md` for full details, success criteria, and requirement mapping.**

## System Requirements

### Hardware
- **12GB RAM** (primary), scales to more
- Local machine or WSL2 environment
- ~10GB disk for LLM model + logs

### Software
- **Python 3.10+** (asyncio-based)
- **Ollama** (local LLM inference)
- **llama3.2:1b** (starting point, quantized)
- **Discord.py** (Discord bot)
- **FastAPI** (web framework)
- **SQLite** (persistent emotional state)
- **Whisper** (STT, later phases)
- **pyttsx3** (TTS, later phases)

### Network
- Stable internet connection (only for Ollama model download + Discord)
- Local network access to Android phone (Wi-Fi)

## Ramble Configuration

Demi posts spontaneous rambles to Discord when emotionally triggered.

**Setup:**

1. **Create a Discord channel:** `#demi-rambles`
2. **Get channel ID:** Right-click channel → Copy Channel ID (enable Developer Mode first)
3. **Set environment variable:**
   ```bash
   export DISCORD_RAMBLE_CHANNEL_ID=<your-channel-id>
   ```

**Ramble Triggers:**

Demi will post spontaneous thoughts when:
- **Lonely** (loneliness > 0.7) - Missing interaction, seeking connection
- **Excited** (excitement > 0.8) - Feeling social, has something to share
- **Frustrated** (frustration > 0.6) - Needs to vent, express feelings

**Spam Prevention:**

Rambles post at most **every 60 minutes** to avoid overwhelming the channel.

## Unified Emotional State (Android + Discord)

Demi has **ONE** emotional state shared across all platforms.

- Discord conversation increases affection → Android messages warmer
- Android loneliness triggers Discord check-ins
- Frustration from Android errors affects Discord responses

**Implementation:** EmotionPersistence stores single state in database, loaded by all platforms.

## Getting Started

1. **Read the project docs**
   ```bash
   cat .planning/PROJECT.md      # Understand Demi's vision
   cat .planning/REQUIREMENTS.md # See v1 requirements
   cat .planning/ROADMAP.md      # Understand build order
   cat DEMI_PERSONA.md           # Know her personality
   ```

2. **Set up environment**
   ```bash
   python -m venv venv
   source venv/bin/activate       # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Ollama & llama3.2:1b**
   ```bash
   # https://ollama.ai
   ollama pull llama3.2:1b
   ollama serve                  # Keep running in another terminal
   ```

4. **Start Phase 1 planning**
   ```bash
   /gsd:plan-phase 1
   ```

## Tech Stack

**Core:**
- Python 3.10+ with asyncio (single event loop, minimal overhead)
- FastAPI (async web framework)
- Ollama + llama3.2:1b (local LLM inference)

**Integrations:**
- discord.py 2.5+ (Discord bot)
- FastAPI + Starlette (Android REST API)
- Whisper (STT) + pyttsx3 (TTS)

**Data:**
- SQLite (emotional state persistence)
- JSON (ramble logs, configuration)

**See `.planning/research/STACK.md` for full rationale and alternatives.**

## Development Philosophy

- **Authenticity first** → Personality must feel real, not forced
- **Emotional consistency** → Moods persist and decay naturally
- **Graceful degradation** → One platform failure never crashes entire system
- **Local autonomy** → No cloud APIs, no external dependencies (except Discord)
- **Solo dev friendly** → Single Python process, simple architecture

## Known Constraints

- **Memory:** 12GB initial, auto-scales integrations down if needed
- **LLM size:** Starting with 1B model; scales to 7B/13B/70B as RAM allows
- **Single user:** v1 is personal to you, not multi-user
- **No production hardening:** v1 is MVP quality; Phase 2+ adds monitoring/failsafes

## Project Status

- ✅ **Questioning:** Deep context gathering complete
- ✅ **Research:** 4 parallel researchers completed (stack, features, architecture, pitfalls)
- ✅ **Requirements:** 40 v1 requirements defined and scoped
- ✅ **Roadmap:** 10-phase implementation plan with 100% requirement coverage
- 🔵 **Phase 1:** Ready to plan and execute

**Next:** `/gsd:plan-phase 1` to begin detailed Phase 1 planning

---

**Last Updated:** 2026-02-01 (Project initialized with full research & roadmap)
