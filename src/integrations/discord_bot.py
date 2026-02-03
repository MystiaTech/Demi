"""Discord bot integration for Demi.

Provides Discord presence, message routing, and bidirectional communication.
Includes voice channel integration for voice commands and responses.
"""

import os
import sys
import asyncio
import uuid
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

from src.platforms.base import BasePlatform, PluginHealth
from src.core.logger import get_logger
from src.models.rambles import Ramble, RambleStore
from src.autonomy.coordinator import AutonomyCoordinator

# Voice integration (optional)
try:
    from src.integrations.discord_voice import DiscordVoiceClient, VoiceSession
    HAS_VOICE = True
except ImportError:
    HAS_VOICE = False
    DiscordVoiceClient = None
    VoiceSession = None


# Emotion to Discord color mapping
EMOTION_COLORS = {
    "loneliness": discord.Color.purple(),  # 0x9370DB
    "excitement": discord.Color.green(),  # 0x2ECC71
    "frustration": discord.Color.red(),  # 0xE74C3C
    "affection": discord.Color.magenta(),  # 0xFF1493 (hot pink)
    "confidence": discord.Color.blue(),  # 0x3498DB
    "curiosity": discord.Color.teal(),  # 0x1ABC9C (cyan)
    "jealousy": discord.Color.orange(),  # 0xE67E22
    "vulnerability": discord.Color.magenta(),  # 0xD946EF
    "defensiveness": discord.Color.dark_gray(),  # 0x36393B
}


def get_dominant_emotion(emotion_state: Optional[Dict]) -> tuple[str, discord.Color]:
    """
    Given emotion_state dict with emotion dimensions, find dominant emotion.

    Args:
        emotion_state: Dict like {"loneliness": 0.5, "excitement": 0.8, ...}

    Returns:
        Tuple of (emotion_name, discord.Color)

    Example:
        emotion, color = get_dominant_emotion({"excitement": 0.8, "loneliness": 0.2})
        # Returns ("excitement", discord.Color.green())
    """
    if not emotion_state:
        return "neutral", discord.Color.blurple()  # Discord blurple as fallback

    max_emotion = max(emotion_state.items(), key=lambda x: x[1])
    emotion_name = max_emotion[0]
    color = EMOTION_COLORS.get(emotion_name, discord.Color.blurple())
    return emotion_name, color


def format_response_as_embed(
    response_dict: Dict, user_name: str = "User"
) -> discord.Embed:
    """
    Format LLM response as Discord embed with emotion visualization.

    Args:
        response_dict: Response from conductor.request_inference() with keys:
            - "content": str (the message text)
            - "emotion_state": Dict (emotional state before response)
            - "message_id": str (optional, for tracking)
        user_name: Name of user who sent message (for reply context)

    Returns:
        discord.Embed ready to send
    """
    content = response_dict.get("content", "Error generating response")
    emotion_state = response_dict.get("emotion_state", {})
    message_id = response_dict.get("message_id", "")

    # Get dominant emotion for color
    dominant_emotion, color = get_dominant_emotion(emotion_state)

    # Create embed
    embed = discord.Embed(
        title=f"Demi's Response",
        description=content[:2000],  # Discord 2000 char limit per embed description
        color=color,
    )

    # Add emotion indicator as footer
    emotion_display = dominant_emotion.replace("_", " ").title()
    embed.set_footer(text=f"Mood: {emotion_display} | Demi v1")

    # Add timestamp
    embed.timestamp = discord.utils.utcnow()

    # Optional: Add emotion breakdown as field (if verbose mode)
    # This is hidden by default but could be shown in responses
    if len(emotion_state) > 0 and any(v > 0.5 for v in emotion_state.values()):
        # Create compact emotion summary (only show emotions > 0.3)
        strong_emotions = [
            f"{e.replace('_', ' ').title()}: {v:.1f}"
            for e, v in emotion_state.items()
            if v > 0.3
        ]
        if strong_emotions and len(strong_emotions) <= 3:
            emotion_summary = " | ".join(strong_emotions)
            embed.add_field(
                name="Emotional Context", value=emotion_summary, inline=False
            )

    return embed


def should_generate_ramble(
    emotion_state: Dict[str, float],
    last_ramble_time: Optional[datetime] = None,
    min_interval_minutes: int = 60,
) -> tuple[bool, Optional[str]]:
    """
    Decide if Demi should post a ramble now.

    Rules:
    - Loneliness > 0.7 → ramble (missing interaction)
    - Excitement > 0.8 → ramble (feeling social)
    - Frustration > 0.6 → ramble (venting)
    - Don't ramble more than every 60 minutes (prevents spam)

    Args:
        emotion_state: Dict of emotion values (e.g., {"loneliness": 0.8})
        last_ramble_time: When last ramble was posted (for interval check)
        min_interval_minutes: Minimum minutes between rambles (default 60)

    Returns:
        (should_ramble: bool, trigger: Optional[str])
    """
    if not emotion_state:
        return False, None

    # Check if enough time since last ramble
    if last_ramble_time:
        if datetime.now(timezone.utc) - last_ramble_time < timedelta(
            minutes=min_interval_minutes
        ):
            return False, None

    # Check emotional triggers
    if emotion_state.get("loneliness", 0) > 0.7:
        return True, "loneliness"

    if emotion_state.get("excitement", 0) > 0.8:
        return True, "excitement"

    if emotion_state.get("frustration", 0) > 0.6:
        return True, "frustration"

    return False, None


class RambleTask:
    """Scheduled task for posting spontaneous rambles"""

    def __init__(self, bot: commands.Bot, conductor, ramble_store: RambleStore, logger):
        """Initialize ramble task.

        Args:
            bot: Discord bot instance
            conductor: Conductor instance for LLM inference
            ramble_store: RambleStore for persistence
            logger: Logger instance
        """
        self.bot = bot
        self.conductor = conductor
        self.ramble_store = ramble_store
        self.logger = logger
        self.last_ramble_time = None
        self.ramble_channel_id = int(os.getenv("DISCORD_RAMBLE_CHANNEL_ID", "0"))

        if self.ramble_channel_id:
            self.ramble_loop.start()
        else:
            self.logger.warning(
                "DISCORD_RAMBLE_CHANNEL_ID not set - ramble posting disabled"
            )

    @tasks.loop(minutes=15)  # Check every 15 minutes
    async def ramble_loop(self):
        """Check if Demi should ramble, generate and post if so"""
        try:
            # Get current emotion state
            from src.emotion.persistence import EmotionPersistence

            emotion_persist = EmotionPersistence()  # Uses default DB path
            emotion_state_obj = emotion_persist.load_latest_state()

            # Convert to dict for decision logic
            emotion_state = (
                emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
            )

            # Check if should ramble
            should_ramble, trigger = should_generate_ramble(
                emotion_state, self.last_ramble_time, min_interval_minutes=60
            )

            if not should_ramble:
                self.logger.debug("No ramble trigger met")
                return

            self.logger.info(f"Generating ramble (trigger: {trigger})")

            # Generate ramble content via LLM pipeline
            prompt_addendum = self._get_ramble_prompt(trigger, emotion_state_obj)

            # Format as LLM messages
            messages = [{"role": "user", "content": prompt_addendum}]

            response = await self.conductor.request_inference(messages)

            # Extract content from response (handle both dict and string)
            if isinstance(response, dict):
                content = response.get("content", "")
            else:
                content = response

            # Post to ramble channel
            channel = self.bot.get_channel(self.ramble_channel_id)
            if channel:
                # Format as embed with ramble indication
                response_dict = {"content": content, "emotion_state": emotion_state}
                embed = format_response_as_embed(response_dict, "Demi")
                embed.title = "💭 Demi's Thoughts"  # Visual ramble indicator

                await channel.send(embed=embed)
                self.logger.info(f"Ramble posted: {len(content)} chars")

                # Store ramble
                ramble = Ramble(
                    ramble_id=str(uuid.uuid4()),
                    channel_id=str(self.ramble_channel_id),
                    content=content,
                    emotion_state=emotion_state,
                    trigger=trigger,
                    created_at=datetime.now(timezone.utc),
                )
                await self.ramble_store.save(ramble)
                self.last_ramble_time = datetime.now(timezone.utc)
            else:
                self.logger.error(f"Ramble channel {self.ramble_channel_id} not found")

        except Exception as e:
            self.logger.error(f"Ramble generation failed: {e}")

    @ramble_loop.before_loop
    async def before_ramble(self):
        """Wait for bot to be ready before starting ramble loop"""
        await self.bot.wait_until_ready()

    def _get_ramble_prompt(self, trigger: str, emotion_state) -> str:
        """
        Get the prompt to add to LLM for ramble generation.
        Different prompts for different triggers.

        Args:
            trigger: Trigger type ("loneliness", "excitement", "frustration")
            emotion_state: EmotionalState object (unused for now)

        Returns:
            Prompt string for LLM
        """
        if trigger == "loneliness":
            return "I'm feeling a bit lonely. What's on my mind? (Generate a spontaneous, personal thought in first person, 1-2 sentences)"
        elif trigger == "excitement":
            return "I'm excited about something. What would I express right now? (Generate a spontaneous, enthusiastic thought in first person, 1-2 sentences)"
        elif trigger == "frustration":
            return "I'm frustrated. What would I vent about? (Generate a spontaneous, honest complaint in first person, 1-2 sentences)"
        else:
            return "What's on my mind? (Generate a spontaneous thought in first person, 1-2 sentences)"

    def stop(self):
        """Stop ramble loop"""
        if self.ramble_loop.is_running():
            self.ramble_loop.stop()


class DiscordBot(BasePlatform):
    """Discord bot platform integration.

    Routes Discord messages (mentions and DMs) to Conductor's LLM pipeline
    and sends responses back through Discord channels.
    """

    def __init__(self):
        """Initialize Discord bot."""
        super().__init__()
        self._name = "discord"
        self._status = "offline"

        self.logger = get_logger()
        self.bot: Optional[commands.Bot] = None
        self.token: Optional[str] = None
        self.conductor = None
        self._initialized = False
        self._bot_task: Optional[asyncio.Task] = None
        self.autonomy_coordinator: Optional[AutonomyCoordinator] = None
        self.voice_client: Optional[DiscordVoiceClient] = None

    def initialize(self, config: dict) -> bool:
        """Initialize Discord bot with intents and event handlers.

        Args:
            config: Configuration dictionary for Discord

        Returns:
            True if initialization successful
        """
        try:
            # Load token from environment
            self.token = os.getenv("DISCORD_BOT_TOKEN")
            if not self.token:
                raise ValueError(
                    "DISCORD_BOT_TOKEN environment variable not set. "
                    "Get token from Discord Developer Portal → Applications → [Your App] → Bot"
                )

            if len(self.token.strip()) == 0:
                raise ValueError("DISCORD_BOT_TOKEN is empty")

            # Configure intents
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message.content
            intents.guilds = True  # Required for server messages
            intents.dm_messages = True  # Required for DM handling

            # Create bot instance
            self.bot = commands.Bot(command_prefix="!", intents=intents)

            # Register event handlers
            print(f"📌 Registering Discord event handlers...")
            self.logger.info("Registering Discord event handlers")

            @self.bot.event
            async def on_ready():
                """Bot connected and ready."""
                try:
                    self.logger.info(
                        f"Discord bot connected as {self.bot.user}",
                        bot_id=self.bot.user.id,
                        guild_count=len(self.bot.guilds),
                    )
                    print(f"\n{'='*60}")
                    print(f"✅ DISCORD BOT ONLINE!")
                    print(f"   Bot: {self.bot.user}")
                    print(f"   User ID: {self.bot.user.id}")
                    print(f"   Servers: {len(self.bot.guilds)}")
                    print(f"   Status: Ready to respond!")
                    print(f"{'='*60}\n")
                    self._status = "online"
                except Exception as e:
                    self.logger.error(f"Error in on_ready handler: {e}")
                    print(f"❌ Error in on_ready: {e}")

            @self.bot.event
            async def on_error(event, *args, **kwargs):
                """Handle bot errors."""
                exc_type, exc_value, exc_traceback = sys.exc_info()
                self.logger.error(f"Discord bot error in {event}: {exc_value}")
                print(f"❌ Discord bot error in {event}: {exc_value}")

            self.logger.info("Event handlers registered")

            @self.bot.event
            async def on_message(message):
                """Handle incoming messages (mentions and DMs)."""
                # Ignore bot's own messages
                if message.author == self.bot.user:
                    return

                # Ignore other bots
                if message.author.bot:
                    return

                # Check if message is a mention or DM
                is_mention = self.bot.user.mentioned_in(message)
                is_dm = isinstance(message.channel, discord.DMChannel)

                if not (is_mention or is_dm):
                    return  # Ignore messages not directed at Demi

                # Extract context
                user_id = str(message.author.id)
                guild_id = str(message.guild.id) if message.guild else None
                channel_id = str(message.channel.id)

                # Extract message content (remove bot mention if present)
                content = message.content
                if is_mention:
                    # Strip bot mention from content
                    for mention_str in [
                        f"<@{self.bot.user.id}>",
                        f"<@!{self.bot.user.id}>",
                    ]:
                        content = content.replace(mention_str, "").strip()

                # Log interaction
                self.logger.info(
                    "Discord message received",
                    user_id=user_id,
                    guild_id=guild_id,
                    is_dm=is_dm,
                    content_length=len(content),
                )
                print(f"💬 Discord message from {message.author}: {content[:50]}..." if len(content) > 50 else f"💬 Discord message from {message.author}: {content}")

                # Skip empty messages after mention removal
                if not content or len(content) == 0:
                    return

                # Check if conductor is available
                if not self.conductor:
                    await message.reply("I'm not ready yet. Try again in a moment.", mention_author=False)
                    return

                try:
                    # Show typing indicator (improves UX)
                    async with message.channel.typing():
                        # Route through Conductor
                        # Format message for LLM (simple format for now, will be enhanced in future plans)
                        messages = [{"role": "user", "content": content}]

                        response = await self.conductor.request_inference(messages)

                    # Format response as embed
                    try:
                        # Handle both dict and string responses (backward compatibility)
                        if isinstance(response, dict):
                            # New format: dict with content and emotion_state
                            embed = format_response_as_embed(
                                response, str(message.author)
                            )
                            await message.reply(embed=embed, mention_author=False)
                            response_text = response.get("content", "")
                        else:
                            # Legacy format: plain string
                            # Wrap in dict for embed formatting
                            response_dict = {"content": response, "emotion_state": {}}
                            embed = format_response_as_embed(
                                response_dict, str(message.author)
                            )
                            await message.reply(embed=embed, mention_author=False)
                            response_text = response
                    except Exception as embed_error:
                        # Fallback to plain text if embed formatting fails
                        self.logger.warning(
                            f"Embed formatting failed, using plain text: {embed_error}",
                            user_id=user_id,
                        )
                        response_text = (
                            response.get("content", response)
                            if isinstance(response, dict)
                            else response
                        )
                        await message.reply(response_text, mention_author=False)

                    self.logger.info(
                        "Discord response sent",
                        user_id=user_id,
                        response_length=len(response_text),
                    )
                    print(f"✅ Response sent: {response_text[:50]}..." if len(response_text) > 50 else f"✅ Response sent: {response_text}")

                except Exception as e:
                    self.logger.error(
                        f"Discord message handling error: {e}",
                        user_id=user_id,
                        error_type=type(e).__name__,
                    )
                    print(f"❌ Error handling message: {str(e)}")
                    # Send error message to user
                    error_msg = "Oops, something went wrong. Try again in a moment."
                    await message.reply(error_msg, mention_author=False)

            # Log successful initialization
            self.logger.info(
                "Discord bot initialized",
                intents=["message_content", "guilds", "direct_messages"],
            )

            # Register voice commands
            self._register_voice_commands()

            self._initialized = True
            self._status = "initialized"

            return True

        except ValueError as e:
            self.logger.error(f"Discord bot configuration error: {e}")
            self._status = "error"
            return False
        except Exception as e:
            self.logger.error(f"Discord bot initialization failed: {e}")
            self._status = "error"
            return False

    def setup(self, conductor) -> bool:
        """Setup Discord bot with conductor reference and start it.

        This is called after initialization to provide the conductor reference
        and actually start the bot.

        Args:
            conductor: Conductor instance for LLM routing

        Returns:
            True if setup successful
        """
        try:
            self.conductor = conductor
            self.logger.info(f"Discord bot setup: Starting bot with token: {self.token[:20]}...")
            print(f"🤖 Discord Bot: Starting connection...")

            # Start bot in background (non-blocking)
            self.logger.info("Creating asyncio task for bot.start()")
            self._bot_task = asyncio.create_task(self.bot.start(self.token))

            # Add callback to catch errors
            def task_error_callback(task):
                try:
                    exc = task.exception()
                    if exc:
                        self.logger.error(f"Discord bot task exception: {exc}")
                        print(f"❌ Discord Bot Error: {exc}")
                except asyncio.CancelledError:
                    self.logger.info("Discord bot task was cancelled")
                except Exception as e:
                    self.logger.error(f"Error in task callback: {e}")

            self._bot_task.add_done_callback(task_error_callback)
            self.logger.info("Bot start task created successfully")

            # Get autonomy coordinator from conductor
            if hasattr(conductor, "autonomy_coordinator"):
                self.autonomy_coordinator = conductor.autonomy_coordinator
                self.logger.info("Connected to unified autonomy system")
            else:
                self.logger.warning("Autonomy coordinator not available in conductor")

            # Initialize voice client if enabled
            voice_enabled = os.getenv("DISCORD_VOICE_ENABLED", "false").lower() == "true"
            if voice_enabled and HAS_VOICE:
                try:
                    self.voice_client = DiscordVoiceClient(self.bot, conductor)
                    self.logger.info("Discord voice client initialized")
                except Exception as e:
                    self.logger.error(f"Voice client initialization failed: {e}")
            elif voice_enabled and not HAS_VOICE:
                self.logger.warning("Voice features enabled but voice module not available")

            self._status = "online"
            self.logger.info("Discord bot setup complete and starting")
            print("✅ Discord bot setup complete - waiting for connection...")
            return True

        except Exception as e:
            self.logger.error(f"Discord bot setup failed: {e}")
            self._status = "error"
            print(f"❌ Discord bot setup failed: {e}")
            return False

    def _register_voice_commands(self):
        """Register voice-related bot commands."""
        
        @self.bot.command(name="join")
        async def join_voice(ctx):
            """Join the user's current voice channel."""
            if not self.voice_client:
                await ctx.reply("Voice features are disabled.", mention_author=False)
                return
            
            if not ctx.author.voice:
                await ctx.reply(
                    "You need to be in a voice channel first, mortal.", 
                    mention_author=False
                )
                return
            
            channel = ctx.author.voice.channel
            success = await self.voice_client.join_channel(channel)
            
            if success:
                embed = discord.Embed(
                    title="🔮 Voice Connected",
                    description="I have arrived. Say 'Demi' to command me.",
                    color=discord.Color.purple()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            else:
                await ctx.reply(
                    "I cannot join that channel.", 
                    mention_author=False
                )
        
        @self.bot.command(name="leave")
        async def leave_voice(ctx):
            """Leave the voice channel."""
            if not self.voice_client:
                await ctx.reply("Voice features are disabled.", mention_author=False)
                return
            
            success = await self.voice_client.leave_channel(ctx.guild.id)
            
            if success:
                embed = discord.Embed(
                    title="👋 Voice Disconnected",
                    description="Call me when you need divine wisdom.",
                    color=discord.Color.purple()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            else:
                await ctx.reply(
                    "I'm not in a voice channel.", 
                    mention_author=False
                )
        
        @self.bot.command(name="voice")
        async def voice_control(ctx, action: Optional[str] = None):
            """Control voice settings: !voice on | !voice off"""
            if not self.voice_client:
                await ctx.reply("Voice features are disabled.", mention_author=False)
                return
            
            session = self.voice_client.get_session(ctx.guild.id)
            if not session:
                await ctx.reply(
                    "I'm not in a voice channel.", 
                    mention_author=False
                )
                return
            
            if action is None:
                # Show current status
                status = "enabled" if self.voice_client.listen_after_response else "disabled"
                await ctx.reply(
                    f"Always-listening mode is currently {status}. Use `!voice on` or `!voice off`.",
                    mention_author=False
                )
                return
            
            if action.lower() == "on":
                self.voice_client.start_listening(ctx.guild.id)
                embed = discord.Embed(
                    title="🎙️ Listening Enabled",
                    description="Always-listening mode on. I hear everything.",
                    color=discord.Color.green()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            
            elif action.lower() == "off":
                self.voice_client.stop_listening(ctx.guild.id)
                embed = discord.Embed(
                    title="🔇 Listening Disabled",
                    description="Wake-word only mode. Say 'Demi' to get my attention.",
                    color=discord.Color.orange()
                )
                await ctx.reply(embed=embed, mention_author=False, delete_after=10)
            
            else:
                await ctx.reply(
                    "Usage: `!voice on` | `!voice off`", 
                    mention_author=False
                )
    
    async def shutdown(self) -> None:
        """Shutdown Discord bot gracefully."""
        try:
            self.logger.info("Discord bot shutting down...")

            # Shutdown voice client
            if self.voice_client:
                await self.voice_client.leave_all_channels()
                self.logger.info("Voice client shutdown")

            # Autonomy system is managed by conductor, no need to stop here

            if self.bot and not self.bot.is_closed():
                await self.bot.close()

            # Cancel background task if running
            if self._bot_task and not self._bot_task.done():
                self._bot_task.cancel()
                try:
                    await self._bot_task
                except asyncio.CancelledError:
                    pass

            self._status = "offline"
            self.logger.info("Discord bot shutdown complete")

        except Exception as e:
            self.logger.error(f"Discord bot shutdown error: {e}")

    def health_check(self) -> PluginHealth:
        """Check Discord bot health.

        Returns:
            PluginHealth with status and response time
        """
        try:
            is_ready = self.bot.is_ready() if self.bot else False

            status = "healthy" if is_ready else "unhealthy"
            error_message = None if is_ready else "Bot not connected to Discord"

            self.logger.debug("Discord health check", status=status, is_ready=is_ready)

            return PluginHealth(
                status=status,
                response_time_ms=0.0,  # Discord doesn't provide latency in is_ready()
                last_check=datetime.now(),
                error_message=error_message,
            )

        except Exception as e:
            self.logger.error(f"Discord health check error: {e}")
            return PluginHealth(
                status="unhealthy",
                response_time_ms=0.0,
                last_check=datetime.now(),
                error_message=str(e),
            )

    def handle_request(self, request: dict) -> dict:
        """Handle platform-specific requests.

        Args:
            request: Request dict with action and parameters

        Returns:
            Response dict with status and data
        """
        # This method is part of BasePlatform interface but not needed
        # for Discord message routing (handled via on_message event)
        return {
            "status": "success",
            "message": "Discord bot uses event-driven message routing",
        }

    def send_message(self, content: str, channel_id: str) -> bool:
        """
        Send message through Discord bot for unified autonomy system.

        Args:
            content: Message content to send
            channel_id: Discord channel ID

        Returns:
            True if message sent successfully
        """
        try:
            if not self.bot or not self.bot.is_ready():
                return False

            # Get channel
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                self.logger.error(f"Discord channel {channel_id} not found")
                return False

            # Create embed for autonomous message
            response_dict = {
                "content": content,
                "emotion_state": {},  # Will be populated by autonomy system
            }
            embed = format_response_as_embed(response_dict, "Demi")
            embed.title = (
                "💭 Demi's Thoughts"  # Visual indicator for autonomous messages
            )

            # Send message
            asyncio.create_task(channel.send(embed=embed))
            self.logger.info(f"Autonomous Discord message sent to channel {channel_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send autonomous Discord message: {e}")
            return False
