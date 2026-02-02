# Phase 05: Discord Integration - Discovery

**Researched:** 2026-02-02  
**Research Scope:** discord.py bot framework, intents & permissions, message handling, embed formatting, channel management, DM routing, rate limiting, async event loop integration  
**Status:** Complete - Ready for planning

---

## Executive Summary

Phase 05 integrates Demi as a Discord bot with full LLM pipeline integration. Research across discord.py documentation, Discord API best practices, and async bot architecture reveals:

1. **discord.py framework** provides high-level bot abstraction with event handlers, message routing, and permission management
2. **Bot intents** control which events Discord fires; GUILDS + MESSAGE_CONTENT required for mention/DM handling (default intents insufficient)
3. **Message handling** routes to LLM pipeline via Conductor, returns formatted responses with embeds for personality/emotion
4. **Ramble posting** uses scheduled tasks (discord.ext.tasks) for spontaneous messages to dedicated channels
5. **Process isolation** prevents Discord failures from cascading to other integrations via Conductor's router

---

## 1. discord.py Framework Architecture

### Bot Setup Pattern

```python
from discord.ext import commands
import discord

intents = discord.Intents.default()
intents.message_content = True  # Required for message.content access
intents.guilds = True
intents.direct_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore own messages
    
    # Process message through LLM pipeline
    response = await llm_pipeline.process(message.content)
    await message.reply(response)

bot.run(token)  # Blocking call - runs event loop
```

### Key Concepts

| Concept | Purpose | Demi Impact |
|---------|---------|------------|
| **Intents** | Filter events Discord sends to bot | Need GUILDS, MESSAGE_CONTENT, DIRECT_MESSAGES, GUILD_MESSAGE_REACTIONS |
| **Events** | Async callbacks (on_message, on_ready, etc.) | message handlers, startup/shutdown |
| **Message Routing** | Which handler processes which message | Mentions → LLM, DMs → LLM, Reactions → potential future |
| **Embeds** | Rich message formatting with color, fields | Personality display (emotion state, metadata) |
| **Channels** | Text/voice containers | Ramble channel, command channel (future) |
| **Rate Limiting** | Discord API throttling (100 requests/min) | Conductor handles via request router |

---

## 2. Message Handling Architecture

### Event Flow: Discord Message → Demi Response

1. **on_message** fires (Discord event)
2. Check: Is this a mention of @Demi or a DM?
3. Extract message context (author, channel, guild, timestamp)
4. **Request Router** (Conductor) routes to discord platform
5. **LLM Pipeline**:
   - Emotion state retrieved
   - Conversation history loaded
   - Prompt built with emotional modulation
   - Inference (llama3.2:1b)
   - Response processing
6. **Format for Discord** (embeds, text, reactions)
7. Send response to channel/DM

### Mention Detection

```python
@bot.event
async def on_message(message):
    # Bot mention: <@123456789> or @Demi
    if bot.user.mentioned_in(message):
        # Process
    elif isinstance(message.channel, discord.DMChannel):
        # Process DMs
```

### DM Routing

DMs need special handling - they're private conversations between user and Demi, not shared in servers. Store separately with user_id as key.

---

## 3. Ramble System (Spontaneous Messages)

### What are Rambles?

Autonomously generated messages posted by Demi when:
- Lonely (loneliness > 0.7, idle >1 hour)
- Excited (excitement > 0.8, after positive interaction)
- Frustrated (frustration > 0.6, after errors)

### Implementation Pattern

```python
from discord.ext import tasks
import asyncio

class RambleTask:
    def __init__(self, bot, llm_pipeline, emotion_system):
        self.bot = bot
        self.llm = llm_pipeline
        self.emotion = emotion_system
        self.ramble_loop.start()
    
    @tasks.loop(minutes=15)  # Check every 15 minutes
    async def ramble_loop(self):
        if should_ramble(self.emotion):
            channel = get_ramble_channel()
            message = await self.llm.generate_ramble()
            await channel.send(message)
    
    @ramble_loop.before_loop
    async def before_ramble(self):
        await self.bot.wait_until_ready()
```

### Ramble Channel Configuration

- Dedicated channel (e.g., #demi-rambles)
- Only Demi posts (via permission lock)
- Logged to database for emotion tracking
- Each ramble updates interaction log with event type SPONTANEOUS_RAMBLE

---

## 4. Embed Formatting for Personality

### Discord Embeds Overview

```python
embed = discord.Embed(
    title="Response Title",
    description="Main response text",
    color=discord.Color.blue()
)
embed.add_field(name="Emotion State", value="Excited 📊", inline=False)
embed.set_footer(text="Demi v1 | Emotional AI")

await message.reply(embed=embed)
```

### Demi's Embed Strategy

- **Main response:** In `description` field
- **Emotion indicator:** Color based on dominant emotion (blue=calm, red=frustrated, green=excited, purple=lonely)
- **Optional metadata:** Fields for confidence, conversation turn count (hidden unless verbose mode)
- **Fallback:** Plain text if embeds disabled

Emotion → Color Mapping:
- Lonely → Purple (#9370DB)
- Excited → Green (#2ECC71)
- Frustrated → Red (#E74C3C)
- Confident → Blue (#3498DB)
- Affectionate → Pink (#FF69B4)
- Curious → Cyan (#1ABC9C)
- Jealous → Orange (#E67E22)
- Vulnerable → Magenta (#D946EF)
- Defensive → Dark Gray (#36393B)

---

## 5. Integration with Conductor

### Platform Plugin Architecture

Discord bot must be a Conductor plugin:

```python
# src/integrations/discord_bot.py

from src.platforms.base import BasePlatform
from discord.ext import commands

class DiscordBot(BasePlatform):
    name = "discord"
    
    async def initialize(self, conductor):
        # Set up discord.py bot with intents
        self.conductor = conductor
        self.bot = commands.Bot(...)
        
        @self.bot.event
        async def on_message(message):
            # Route through conductor.request_inference()
            response = await conductor.request_inference(
                platform="discord",
                user_id=str(message.author.id),
                content=message.content,
                context={
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "channel_id": str(message.channel.id),
                    "is_dm": isinstance(message.channel, discord.DMChannel),
                }
            )
            await format_and_send(response, message)
    
    async def shutdown(self):
        await self.bot.close()
```

### Resource Management

Discord bot considerations:
- **Memory:** ~50-100MB baseline (websocket + event handlers)
- **CPU:** Minimal when idle (events only fire on message/reaction)
- **Threads:** Runs on asyncio event loop (same as FastAPI can share)
- **Rate limiting:** Discord enforces 100 requests/minute globally; Conductor router queues excess

---

## 6. Database Schema for Discord State

### Tables to Create/Use

| Table | Purpose | Fields |
|-------|---------|--------|
| discord_users | User tracking | user_id, username, first_seen, last_seen |
| discord_guilds | Server tracking | guild_id, guild_name, first_seen |
| discord_conversations | Per-user/guild conversations | conversation_id, user_id, guild_id, messages (JSON), created_at |
| discord_rambles | Spontaneous posts | ramble_id, channel_id, content, emotion_state (JSON), created_at |

### Conversation Storage

Store last N messages per user per guild to maintain context:
- DMs: Store all (or last 100) per user
- Guild mentions: Store last 10 per user per guild (conversation threads are separate)

---

## 7. Rate Limiting & Backpressure

### Discord API Limits

- **Per-channel:** 10 requests/10 seconds (sent messages)
- **Global:** 100 requests/minute (all endpoints)
- **Cooldown:** Automatic 429 Conflict responses with Retry-After header

### Demi's Mitigation

1. Conductor's request router queues messages if bot exceeds per-channel limit
2. Discord.py library handles 429s automatically with exponential backoff
3. Ramble system spreads posts across multiple channels if available

---

## 8. Error Handling & Resilience

### Common Failure Modes

| Failure | Cause | Recovery |
|---------|-------|----------|
| WebSocket disconnect | Network glitch, Discord server restart | discord.py auto-reconnect with exponential backoff |
| Permission denied | Bot lacks Send Messages permission | Log error, silent failure (don't spam user with bot can't send) |
| Message not found | Message deleted before reply | Log error, silent failure |
| LLM timeout | Inference >10 seconds | Return timeout message from template |
| Rate limit | Too many messages queued | Queue in DeadLetterQueue, retry later |

### Circuit Breaker Strategy

Conductor tracks Discord health:
- Health check: Send test message to designated test channel every 30 seconds
- If 3 consecutive checks fail: Mark Discord as DOWN
- Disable new Discord requests, queue in DLQ
- Re-enable when health check passes again

---

## 9. Token Management

### Discord Bot Token

- **How to get:** Discord Developer Portal → Applications → Bot → Copy Token
- **Where to store:** Environment variable DISCORD_BOT_TOKEN
- **Security:** Never commit to repo, never log token
- **Rotation:** Regenerate if compromised (invalidates old token immediately)

### User Setup Requirement

User must:
1. Create Discord application in Developer Portal
2. Create bot user for application
3. Add OAuth2 scopes: bot
4. Add permissions: Send Messages, Embed Links, Read Message History, React to Messages
5. Get invite link: `https://discord.com/api/oauth2/authorize?...`
6. Accept invite in their server(s)
7. Set environment variable DISCORD_BOT_TOKEN

---

## 10. Testing Strategy

### Unit Tests

- Message parsing (extract content, metadata)
- Embed formatting (color selection, field construction)
- Ramble decision logic (should_ramble function)
- Database operations (store/retrieve conversations)

### Integration Tests

- Mock Discord bot with discord.py test framework
- Simulate on_message events
- Verify Conductor integration points
- Test error recovery (network failures, timeouts)

### E2E Tests (Live Discord)

- Create test Discord server with test bot
- Send mention: verify response generated and sent
- Send DM: verify DM response generated and sent
- Check database: verify conversation stored
- Verify emotion state updated

---

## Decision: Discord.py vs discord-py-interactions

**Chose:** discord.py (traditional)

**Reasons:**
- Larger community, more examples
- Stable API, long-term maintenance
- Supports all v1 features
- discord-py-interactions less mature for this use case

**Downside:** discord.py development paused (maintainer burnout), but stable enough for MVP.

---

## Summary: Technology Choices

| Choice | Library | Version | Rationale |
|--------|---------|---------|-----------|
| Bot Framework | discord.py | 2.3+ | Stable, proven, large community |
| Message Routing | Conductor plugin system | v1 | Decouple Discord from LLM pipeline |
| Scheduled Tasks | discord.ext.tasks | Built-in | Discord native, no extra dependency |
| Database | SQLite | v1, PostgreSQL v2+ | Leverage existing Demi DB |
| Testing | pytest + discord.py mock | Standard | Integrate with test suite |

---

## Known Unknowns / Risks

### Pre-Planning (Level 2-3)

- [ ] **Discord WebSocket stability:** Will WebSocket stay connected for 24+ hours without drops?
  - Action: Test with 7-day stability run (Phase 9)
  - Risk Level: MEDIUM

- [ ] **Message latency:** Can responses be generated + sent <2 seconds on target hardware?
  - Action: Benchmark Conductor latency under Discord load (Phase 5 execution)
  - Risk Level: MEDIUM (could force inference model downgrade)

- [ ] **Embed formatting:** Do embeds render correctly with emotional metadata?
  - Action: Visual QA on actual Discord client (Phase 5 verification checkpoint)
  - Risk Level: LOW (worst case: fall back to plain text)

---

## Setup Requirements

**For User (Phase 05 plan frontmatter):**

```yaml
user_setup:
  - service: discord
    why: "Discord bot integration for Demi"
    account_setup:
      - task: "Create Discord application"
        location: "Discord Developer Portal (discord.com/developers/applications)"
    env_vars:
      - name: DISCORD_BOT_TOKEN
        source: "Discord Developer Portal → Applications → [Your App] → Bot → Copy Token"
    dashboard_config:
      - task: "Add OAuth2 scopes (bot) and permissions (Send Messages, Embed Links)"
        location: "Discord Developer Portal → OAuth2 → Scopes & Permissions"
      - task: "Generate invite link and accept in your server(s)"
        location: "OAuth2 invite link from above"
```

---

