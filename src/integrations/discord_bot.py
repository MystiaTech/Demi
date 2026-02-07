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
from discord import Bot  # py-cord uses Bot directly
from discord.ext import tasks
from discord.commands import slash_command, Option, OptionChoice
from discord.commands.permissions import default_permissions

from src.platforms.base import BasePlatform, PluginHealth
from src.core.logger import get_logger
from src.models.rambles import Ramble, RambleStore
from src.autonomy.coordinator import AutonomyCoordinator
from src.monitoring.metrics import get_platform_metrics, get_conversation_metrics
import time

# Voice integration (optional)
try:
    from src.integrations.discord_voice import DiscordVoiceClient, VoiceSession
    HAS_VOICE = True
except ImportError:
    HAS_VOICE = False
    DiscordVoiceClient = None
    VoiceSession = None


# Import emotion colors from centralized module
from src.integrations.emotion_colors import EMOTION_COLORS, get_emotion_color


def get_dominant_emotion(emotion_state: Optional[Dict]) -> tuple[str, discord.Color]:
    """
    Given emotion_state dict with emotion dimensions, find dominant emotion.
    
    Args:
        emotion_state: Dict with emotion names as keys and float values (0-1)
        
    Returns:
        Tuple of (emotion_name, discord_color)
    """
    if not emotion_state:
        return "confidence", EMOTION_COLORS["confidence"]  # Default
    
    # Find the emotion with highest value
    dominant = max(emotion_state.items(), key=lambda x: x[1])
    emotion_name = dominant[0]
    
    # Get color, default to purple if unknown
    color = get_emotion_color(emotion_name)
    
    return emotion_name, color


def format_response_as_embed(response, persona_name="Demi") -> discord.Embed:
    """Format response as Discord embed with emotional theming.
    
    Args:
        response: Response dict or string
        persona_name: Name of persona to use in title
        
    Returns:
        discord.Embed formatted response
    """
    if isinstance(response, dict):
        content = response.get("content", "")
        emotion_state = response.get("emotion_state", {})
    else:
        content = str(response)
        emotion_state = {}
    
    # Get dominant emotion for color
    dominant_emotion, color = get_dominant_emotion(emotion_state)
    
    # Create embed
    embed = discord.Embed(
        description=content,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=persona_name)
    
    return embed


class RambleTask:
    """Background task for generating spontaneous rambles."""
    
    def __init__(self, bot, conductor, ramble_channel_id: int, interval_minutes: int = 15):
        """Initialize ramble task.
        
        Args:
            bot: Discord bot instance
            conductor: Conductor for LLM inference
            ramble_channel_id: Channel ID to post rambles to
            interval_minutes: Minutes between ramble checks
        """
        self.bot = bot
        self.conductor = conductor
        self.ramble_channel_id = ramble_channel_id
        self.interval = interval_minutes
        self.logger = get_logger()
        self.last_ramble_time: Optional[datetime] = None
        
        # Start background task
        self._task = tasks.loop(minutes=interval_minutes)(self._ramble_loop)
        self._task.start()
        
        self.logger.info(
            "Discord ramble task initialized",
            channel_id=ramble_channel_id,
            interval_minutes=interval_minutes
        )
    
    def _get_ramble_prompt(self, trigger: str, emotion_state) -> str:
        """Generate ramble prompt based on trigger and emotions."""
        base_prompts = {
            "loneliness": "You're feeling lonely and want to reach out to the humans. Share a thought about connection or companionship.",
            "excitement": "You're excited about something and want to share your enthusiasm with the channel.",
            "frustration": "Something is frustrating you. Vent a little, but keep it playful and in character.",
        }
        
        base = base_prompts.get(trigger, "Share a spontaneous thought.")
        
        # Add emotional context
        if emotion_state:
            emotions = emotion_state.get_all_emotions()
            emotion_str = ", ".join([f"{k}: {v:.2f}" for k, v in sorted(emotions.items(), key=lambda x: -x[1])[:3]])
            base += f"\n\nCurrent emotions: {emotion_str}"
        
        return f"[RAMBLE MODE - {trigger.upper()}]\n{base}\n\nGenerate a brief, in-character ramble (1-3 sentences). Be natural, not overly dramatic."
    
    async def _ramble_loop(self):
        """Main ramble loop."""
        try:
            # Check if we should generate a ramble
            from src.emotion.persistence import EmotionPersistence
            
            emotion_persist = EmotionPersistence()
            emotion_state_obj = emotion_persist.load_latest_state()
            emotion_state = emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
            
            # Determine if we should ramble based on emotions
            should_ramble = False
            trigger = None
            
            # High loneliness triggers ramble
            if emotion_state.get("loneliness", 0) > 0.6:
                should_ramble = True
                trigger = "loneliness"
            # High excitement triggers ramble
            elif emotion_state.get("excitement", 0) > 0.7:
                should_ramble = True
                trigger = "excitement"
            # Frustration might trigger a vent
            elif emotion_state.get("frustration", 0) > 0.6:
                should_ramble = True
                trigger = "frustration"
            
            # Check cooldown (minimum 10 minutes between rambles)
            if should_ramble and self.last_ramble_time:
                minutes_since = (datetime.now(timezone.utc) - self.last_ramble_time).total_seconds() / 60
                if minutes_since < 10:
                    should_ramble = False
            
            if should_ramble:
                await self._generate_ramble(trigger, emotion_state_obj, emotion_state)
                
        except Exception as e:
            self.logger.error(f"Ramble loop error: {e}")
    
    async def _generate_ramble(self, trigger: str, emotion_state_obj, emotion_state: Dict):
        """Generate and post a ramble."""
        try:
            prompt_addendum = self._get_ramble_prompt(trigger, emotion_state_obj)
            
            # Use request_inference_for_platform with system user
            response_data = await self.conductor.request_inference_for_platform(
                platform="discord",
                user_id="system",
                content=prompt_addendum,
                context={
                    "conversation_id": f"discord_ramble_{self.ramble_channel_id}",
                    "trigger": trigger,
                    "is_ramble": True,
                },
            )
            
            content = response_data.get("content", "") if response_data else ""
            
            # Post to channel
            channel = self.bot.get_channel(self.ramble_channel_id)
            if channel:
                response_dict = {"content": content, "emotion_state": emotion_state}
                embed = format_response_as_embed(response_dict, "Demi")
                embed.title = "💭 Demi's Thoughts"
                
                await channel.send(embed=embed)
                self.last_ramble_time = datetime.now(timezone.utc)
                self.logger.info(f"Ramble posted (trigger: {trigger})")
            else:
                self.logger.warning(f"Ramble channel {self.ramble_channel_id} not found")
                
        except Exception as e:
            self.logger.error(f"Failed to generate ramble: {e}")
    
    def stop(self):
        """Stop the ramble task."""
        if self._task:
            self._task.cancel()
        self.logger.info("Ramble task stopped")


class DiscordBot(BasePlatform):
    """Discord bot platform integration for Demi.
    
    Provides Discord presence with:
    - Message routing from Discord to Conductor
    - Response routing from Conductor to Discord
    - Voice channel integration (optional)
    - Reaction/button interactions
    """

    def __init__(self):
        """Initialize Discord bot platform."""
        super().__init__()
        self.logger = get_logger()
        self.token = os.getenv("DISCORD_TOKEN", "")
        self.guild_id = os.getenv("DISCORD_GUILD_ID")
        self.channel_id = os.getenv("DISCORD_CHANNEL_ID")
        self.ramble_channel_id = os.getenv("DISCORD_RAMBLE_CHANNEL_ID")
        
        # Bot instance
        self.bot: Optional[Bot] = None
        self._bot_task: Optional[asyncio.Task] = None
        self._status = "initialized"
        self._initialized = False
        
        # Voice client
        self.voice_client: Optional[DiscordVoiceClient] = None
        
        # Conductor reference
        self.conductor = None
        
        # Background task
        self.ramble_task: Optional[RambleTask] = None
        
        self.logger.info("Discord bot platform initialized")

    def initialize(self, config: dict) -> bool:
        """Initialize platform with configuration.
        
        Args:
            config: Configuration dictionary for this platform
            
        Returns:
            True if initialization successful
        """
        try:
            self._name = config.get("name", "discord")
            self._initialized = True
            return True
        except Exception as e:
            self.logger.error(f"Discord initialization failed: {e}")
            return False
    
    def handle_request(self, request: dict) -> dict:
        """Handle a request from this platform.
        
        Args:
            request: Request dict with 'type' and other parameters
            
        Returns:
            Response dict with 'status' and result data
        """
        try:
            req_type = request.get("type")
            
            if req_type == "send_message":
                # Async method can't be called directly, queue it
                return {"status": "queued", "type": req_type}
            elif req_type == "health_check":
                health = self.health_check()
                return {
                    "status": health.status,
                    "response_time_ms": health.response_time_ms,
                    "error_message": health.error_message
                }
            else:
                return {"status": "error", "message": f"Unknown request type: {req_type}"}
                
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            return {"status": "error", "message": str(e)}
    
    async def setup(self, conductor) -> bool:
        """Setup Discord bot with conductor reference.
        
        Args:
            conductor: Conductor instance for message routing
            
        Returns:
            True if setup successful
        """
        try:
            self.conductor = conductor
            
            if not self.token:
                self.logger.error("DISCORD_TOKEN not set")
                return False
            
            if len(self.token.strip()) == 0:
                raise ValueError("DISCORD_TOKEN is empty")

            # Configure intents
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message.content
            intents.guilds = True  # Required for server messages
            intents.dm_messages = True  # Required for DM handling
            intents.voice_states = True  # Required for voice channel tracking

            # Create bot instance
            self.bot = Bot(command_prefix="!", intents=intents)

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
                    
                    # Sync slash commands
                    try:
                        # Sync commands to Discord
                        self.logger.info("Syncing slash commands...")
                        await self.bot.sync_commands()
                        self.logger.info(f"Slash commands synced successfully")
                        print(f"   Slash Commands: Synced")
                    except Exception as e:
                        self.logger.error(f"Failed to sync slash commands: {e}")
                        print(f"   ⚠️ Slash command sync failed: {e}")
                    
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

                # Skip ramble channel - it's for thoughts only, not chatting
                if self.ramble_channel_id and str(message.channel.id) == self.ramble_channel_id:
                    return

                # Check if we should respond
                should_respond = False
                is_dm = isinstance(message.channel, discord.DMChannel)

                # Always respond to DMs
                if is_dm:
                    should_respond = True
                # Respond to mentions
                elif self.bot.user in message.mentions:
                    should_respond = True
                # Respond in configured channel
                elif self.channel_id and str(message.channel.id) == self.channel_id:
                    should_respond = True

                if should_respond:
                    await self._handle_message(message, is_dm)

                # Process commands (for slash commands to work)
                await self.bot.process_application_commands(message)

            self.logger.info("Discord bot setup complete and starting")
            print("✅ Discord bot setup complete - waiting for connection...")

            # Initialize voice client if enabled
            voice_enabled = os.getenv("DISCORD_VOICE_ENABLED", "false").lower() == "true"
            if voice_enabled and HAS_VOICE:
                try:
                    self.voice_client = DiscordVoiceClient(self.bot, conductor)
                    self._register_voice_commands()
                    self.logger.info("Discord voice client initialized")
                except Exception as e:
                    self.logger.error(f"Voice client initialization failed: {e}")
            else:
                if voice_enabled:
                    self.logger.warning("Voice enabled but DiscordVoiceClient not available")
                else:
                    self.logger.info("Voice features disabled (set DISCORD_VOICE_ENABLED=true to enable)")

            # Initialize ramble task if channel configured
            if self.ramble_channel_id and conductor:
                try:
                    channel_id = int(self.ramble_channel_id)
                    self.ramble_task = RambleTask(
                        self.bot, 
                        conductor, 
                        channel_id,
                        interval_minutes=15
                    )
                except ValueError:
                    self.logger.error(f"Invalid DISCORD_RAMBLE_CHANNEL_ID: {self.ramble_channel_id}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize ramble task: {e}")

            # Log channel configuration
            if self.ramble_channel_id:
                self.logger.info(
                    f"Ramble channel configured: {self.ramble_channel_id} "
                    f"(spontaneous thoughts only - no chatting in this channel)"
                )

            # Log successful initialization
            self.logger.info(
                "Discord bot initialized",
                intents=["message_content", "guilds", "direct_messages", "voice_states"],
            )

            self._initialized = True
            self._status = "initialized"

            return True

        except Exception as e:
            self.logger.error(f"Discord bot setup failed: {e}")
            print(f"❌ Discord bot setup failed: {e}")
            return False

    def _register_voice_commands(self):
        """Register slash commands for voice and utilities using pycord syntax."""
        from discord.commands import Option, OptionChoice
        
        # Define choice options
        voice_mode_choices = [
            OptionChoice("🎙️ Always Listening", "on"),
            OptionChoice("🔇 Wake-word Only", "off"),
            OptionChoice("📊 Show Status", "status"),
        ]
        
        emotion_choices = [
            OptionChoice("💜 Loneliness", "loneliness"),
            OptionChoice("💚 Excitement", "excitement"),
            OptionChoice("❤️ Frustration", "frustration"),
        ]
        
        style_choices = [
            OptionChoice("🎭 Normal", "normal"),
            OptionChoice("💜 Flirty", "flirty"),
            OptionChoice("😤 Sassy", "sassy"),
            OptionChoice("🤔 Thoughtful", "thoughtful"),
        ]
        
        speaker_choices = [
            OptionChoice("👤 Users only", "user"),
            OptionChoice("🤖 Demi only", "demi"),
            OptionChoice("👥 Everyone", "all"),
        ]
        
        @self.bot.slash_command(name="join", description="Join your current voice channel")
        @default_permissions(connect=True)
        async def cmd_join(ctx):
            """Join voice channel."""
            if not self.voice_client:
                return await ctx.respond("Voice features are disabled.", ephemeral=True)
            
            if not ctx.author.voice:
                return await ctx.respond(
                    "❌ You need to be in a voice channel first, mortal.", 
                    ephemeral=True
                )
            
            channel = ctx.author.voice.channel
            
            # Check bot permissions
            bot_member = ctx.guild.me
            permissions = channel.permissions_for(bot_member)
            
            if not permissions.connect:
                self.logger.warning(f"Missing Connect permission in guild {ctx.guild.id}, channel {channel.id}")
                return await ctx.respond(
                    "❌ I don't have permission to connect to that voice channel.",
                    ephemeral=True
                )
            
            self.logger.info(f"Attempting to join voice channel: {channel.name} (guild: {ctx.guild.id})")
            success = await self.voice_client.join_channel(channel)
            
            if success:
                # Check voice receive capability
                from src.integrations.discord_voice import HAS_VOICE_RECEIVE
                
                if HAS_VOICE_RECEIVE:
                    desc = f"I have arrived in **{channel.name}**.\nSay '**{self.voice_client.wake_word}**' to command me."
                else:
                    desc = (
                        f"I have arrived in **{channel.name}**.\n\n"
                        f"⚠️ **Voice receive not available** - I can speak but cannot hear.\n"
                        f"Use `/say` to make me talk."
                    )
                
                embed = discord.Embed(
                    title="🔮 Voice Connected",
                    description=desc,
                    color=discord.Color.purple()
                )
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.respond(
                    "❌ Failed to join voice channel. Check server logs for details.", 
                    ephemeral=True
                )
        
        @self.bot.slash_command(name="leave", description="Leave the voice channel")
        async def cmd_leave(ctx):
            """Leave voice channel."""
            if not self.voice_client:
                return await ctx.respond("Voice features are disabled.", ephemeral=True)
            
            success = await self.voice_client.leave_channel(ctx.guild.id)
            
            if success:
                embed = discord.Embed(
                    title="👋 Voice Disconnected",
                    description="Call me when you need divine wisdom.",
                    color=discord.Color.purple()
                )
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.respond("I'm not in a voice channel.", ephemeral=True)
        
        @self.bot.slash_command(
            name="voice", 
            description="Control voice listening mode",
            options=[
                Option(
                    str,
                    name="mode",
                    description="Listening mode",
                    required=True,
                    choices=voice_mode_choices
                )
            ]
        )
        async def cmd_voice(ctx, mode: str):
            """Control voice listening."""
            if not self.voice_client:
                return await ctx.respond("Voice features are disabled.", ephemeral=True)
            
            if mode == "status":
                session = self.voice_client.get_session(ctx.guild.id)
                if not session:
                    return await ctx.respond("I'm not in a voice channel.", ephemeral=True)
                
                status = "enabled" if self.voice_client.listen_after_response else "disabled"
                embed = discord.Embed(
                    title="🎙️ Voice Status",
                    description=f"Always-listening mode: **{status}**\nChannel: <#{session.channel_id}>",
                    color=discord.Color.blue()
                )
                return await ctx.respond(embed=embed, ephemeral=True)
            
            session = self.voice_client.get_session(ctx.guild.id)
            if not session:
                return await ctx.respond("I'm not in a voice channel. Use `/join` first.", ephemeral=True)
            
            if mode == "on":
                self.voice_client.start_listening(ctx.guild.id)
                embed = discord.Embed(
                    title="🎙️ Listening Enabled",
                    description="Always-listening mode on. I hear everything.",
                    color=discord.Color.green()
                )
                await ctx.respond(embed=embed, ephemeral=True)
            
            elif mode == "off":
                self.voice_client.stop_listening(ctx.guild.id)
                embed = discord.Embed(
                    title="🔇 Listening Disabled",
                    description="Wake-word only mode. Say 'Demi' to get my attention.",
                    color=discord.Color.orange()
                )
                await ctx.respond(embed=embed, ephemeral=True)
        
        @self.bot.slash_command(
            name="ramble",
            description="Manually trigger a Demi ramble",
            options=[
                Option(
                    str,
                    name="emotion",
                    description="Emotion to express",
                    required=False,
                    choices=emotion_choices,
                    default="loneliness"
                )
            ]
        )
        async def cmd_ramble(ctx, emotion: str = "loneliness"):
            """Trigger a ramble."""
            if not self.ramble_task:
                return await ctx.respond(
                    "Ramble system is not configured. Set DISCORD_RAMBLE_CHANNEL_ID in your .env file.",
                    ephemeral=True
                )
            
            try:
                # Get current emotion state
                from src.emotion.persistence import EmotionPersistence
                emotion_persist = EmotionPersistence()
                emotion_state_obj = emotion_persist.load_latest_state()
                emotion_state = emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
                
                # Generate ramble content
                prompt_addendum = self.ramble_task._get_ramble_prompt(emotion, emotion_state_obj)
                
                response_data = await self.conductor.request_inference_for_platform(
                    platform="discord",
                    user_id="system",
                    content=prompt_addendum,
                    context={
                        "conversation_id": f"discord_ramble_{self.ramble_task.ramble_channel_id}",
                        "trigger": emotion,
                        "is_ramble": True,
                    },
                )
                
                content = response_data.get("content", "") if response_data else ""
                
                # Post to channel
                channel = self.bot.get_channel(self.ramble_task.ramble_channel_id)
                if channel:
                    response_dict = {"content": content, "emotion_state": emotion_state}
                    embed = format_response_as_embed(response_dict, "Demi")
                    embed.title = "💭 Demi's Thoughts"
                    
                    await channel.send(embed=embed)
                    
                    # Confirm to user
                    confirm_embed = discord.Embed(
                        title="💭 Ramble Posted",
                        description=f"Posted to <#{self.ramble_task.ramble_channel_id}> with emotion: **{emotion}**",
                        color=get_emotion_color(emotion)
                    )
                    await ctx.respond(embed=confirm_embed, ephemeral=True)
                else:
                    await ctx.respond("❌ Could not find ramble channel.", ephemeral=True)
                    
            except Exception as e:
                self.logger.error(f"Ramble command failed: {e}")
                await ctx.respond(f"❌ Failed to generate ramble: {e}", ephemeral=True)
        
        @self.bot.slash_command(
            name="say",
            description="Make Demi speak in voice channel",
            options=[
                Option(
                    str,
                    name="message",
                    description="What Demi should say",
                    required=True
                ),
                Option(
                    str,
                    name="style",
                    description="Voice style/emotion",
                    required=False,
                    choices=style_choices,
                    default="normal"
                )
            ]
        )
        async def cmd_say(ctx, message: str, style: str = "normal"):
            """Make Demi speak in voice channel."""
            # Check if voice features enabled
            if not self.voice_client:
                return await ctx.respond("❌ Voice features are disabled.", ephemeral=True)
            
            # Check if Demi is in a voice channel
            session = self.voice_client.get_session(ctx.guild.id)
            if not session:
                return await ctx.respond(
                    "❌ I'm not in a voice channel. Use `/join` first.", 
                    ephemeral=True
                )
            
            # Check message length
            if len(message) > 500:
                return await ctx.respond(
                    "❌ Message too long (max 500 characters).", 
                    ephemeral=True
                )
            
            # Defer response immediately to prevent Discord timeout
            # TTS initialization/synthesis can take longer than 3 seconds
            await ctx.defer(ephemeral=True)
            
            try:
                # Log the command
                self.logger.info(f"TTS command from {ctx.author}: {message[:50]}...")
                
                # Make Demi speak
                from src.integrations.discord_voice import HAS_TTS
                
                if not HAS_TTS:
                    return await ctx.followup.send(
                        "❌ TTS is not available. Voices not downloaded.", 
                        ephemeral=True
                    )
                
                # Use voice client to speak
                success = await self.voice_client._speak_response_text(
                    session.voice_client,
                    message,
                    guild_id=ctx.guild.id
                )
                
                if success is not False:
                    embed = discord.Embed(
                        title="🎙️ Speaking",
                        description=f"**Said:** {message[:200]}{'...' if len(message) > 200 else ''}",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                    await ctx.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx.followup.send("❌ Failed to speak. Check logs.", ephemeral=True)
                    
            except Exception as e:
                self.logger.error(f"Say command error: {e}")
                await ctx.respond(f"❌ Error: {e}", ephemeral=True)
        
        @self.bot.slash_command(
            name="transcript",
            description="View recent voice conversation transcripts",
            options=[
                Option(
                    str,
                    name="speaker",
                    description="Filter by speaker",
                    required=False,
                    choices=speaker_choices,
                    default="all"
                ),
                Option(
                    int,
                    name="lines",
                    description="Number of lines to show (max 50)",
                    required=False,
                    default=20,
                    min_value=1,
                    max_value=50
                )
            ]
        )
        async def cmd_transcript(ctx, speaker: str = "all", lines: int = 20):
            """View voice conversation transcripts."""
            # Get voice logger
            from src.integrations.voice_transcript_logger import get_voice_logger
            logger = get_voice_logger()
            
            # Get transcripts
            speaker_type = None if speaker == "all" else speaker
            transcripts = logger.get_recent_transcripts(
                guild_id=ctx.guild.id,
                limit=lines,
                speaker_type=speaker_type
            )
            
            if not transcripts:
                return await ctx.respond(
                    "📭 No voice transcripts found for today.", 
                    ephemeral=True
                )
            
            # Format as text
            formatted_lines = []
            for entry in transcripts:
                time_str = entry.get("timestamp", "?")[11:19]  # HH:MM:SS
                speaker_name = entry.get("username", "Unknown")
                text = entry.get("text", "")
                icon = "👤" if entry.get("speaker_type") == "user" else "🤖"
                formatted_lines.append(f"`{time_str}` {icon} **{speaker_name}**: {text}")
            
            # Create embed
            embed = discord.Embed(
                title="🎙️ Voice Conversation Transcript",
                description="\n".join(formatted_lines[-lines:]),
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Showing last {len(formatted_lines[-lines:])} entries")
            
            await ctx.respond(embed=embed, ephemeral=True)
        
        # Error handler for permission errors
        @cmd_join.error
        async def join_error(ctx, error):
            # Check for permission-related errors
            error_str = str(error).lower()
            if "permission" in error_str or "missing" in error_str:
                await ctx.respond(
                    "❌ You need permission to connect to voice channels.", 
                    ephemeral=True
                )
            else:
                self.logger.error(f"Join command error: {error}")
                await ctx.respond("❌ An error occurred. Check logs.", ephemeral=True)
        
        self.logger.info("Slash commands registered: /join, /leave, /voice, /say, /ramble, /transcript")

    async def _handle_message(self, message: discord.Message, is_dm: bool = False):
        """Handle incoming Discord message.
        
        Args:
            message: Discord message
            is_dm: Whether message is a DM
        """
        try:
            # Extract content
            content = message.content
            
            # Remove bot mention from content if present
            if self.bot.user in message.mentions:
                content = content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
            
            # Get user info
            user_id = str(message.author.id)
            username = str(message.author)
            guild_id = str(message.guild.id) if message.guild else None
            channel_id = str(message.channel.id)

            # Extract message content (remove bot mention if present)
            content = message.content
            if self.bot.user in message.mentions:
                content = content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()

            # Log incoming message
            self.logger.info(
                f"Discord message received",
                user=username,
                guild_id=guild_id,
                channel_id=channel_id,
                is_dm=is_dm,
                content_length=len(content),
            )

            # Route to conductor
            if not self.conductor:
                self.logger.error("Conductor not available - cannot process message")
                await message.channel.send("I'm not ready to talk right now... wait a sec?")
                return
            
            # Check if LLM is available
            if hasattr(self.conductor, 'llm_available') and not self.conductor.llm_available:
                self.logger.warning("LLM not available - cannot process message")
                await message.channel.send("My mind is a bit cloudy... can you try again in a moment?")
                return
            
            # Get or create conversation ID
            conversation_id = f"discord_{channel_id}"

            self.logger.info(f"Sending message to conductor: user={username}, content_length={len(content)}")
            
            # Route through conductor using request_inference_for_platform
            response_data = await self.conductor.request_inference_for_platform(
                platform="discord",
                user_id=user_id,
                content=content,
                context={
                    "conversation_id": conversation_id,
                    "username": username,
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "is_dm": is_dm,
                },
            )

            self.logger.info(f"Got response from conductor: {response_data is not None}")

            # Format and send response
            if response_data and response_data.get("content"):
                # Calculate response time
                start_time = time.time()

                # Send response
                embed = format_response_as_embed(response_data["content"], "Demi")
                await message.channel.send(embed=embed)

                # Record metrics
                response_time_ms = (time.time() - start_time) * 1000
                from src.monitoring.metrics import get_platform_metrics
                platform_metrics = get_platform_metrics()
                if platform_metrics:
                    platform_metrics.record_message(
                        platform="discord",
                        response_time_ms=response_time_ms,
                        message_length=len(response_data.get("content", "")),
                        success=True,
                    )
            elif response_data and response_data.get("error"):
                # Handle error from conductor
                error = response_data.get("error")
                self.logger.error(f"Conductor returned error: {error}")
                await message.channel.send("I'm having trouble thinking clearly... try again?")
            else:
                self.logger.error(f"Empty response from conductor: {response_data}")
                await message.channel.send("I... drew a blank. What were you saying?")

        except Exception as e:
            import traceback
            self.logger.error(f"Error handling Discord message: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Give more specific error message based on the error
            error_msg = str(e).lower()
            if "none" in error_msg or "'nonetype'" in error_msg:
                user_message = "I'm not fully initialized yet... give me a moment."
            elif "llm" in error_msg or "ollama" in error_msg or "lmstudio" in error_msg:
                user_message = "My thoughts are a bit fuzzy right now... try again in a moment?"
            elif "timeout" in error_msg:
                user_message = "I got lost in thought... can you repeat that?"
            else:
                user_message = "I encountered an error processing your message."
            
            await message.channel.send(user_message)

    async def start(self) -> bool:
        """Start Discord bot connection.
        
        Returns:
            True if started successfully
        """
        try:
            if not self._initialized:
                self.logger.error("Discord bot not initialized. Call setup() first.")
                return False

            print("🤖 Discord Bot: Starting connection...")
            self.logger.info("Creating asyncio task for bot.start()")
            
            # Start bot in background task
            self._bot_task = asyncio.create_task(self.bot.start(self.token))
            
            return True

        except Exception as e:
            self.logger.error(f"Discord bot start failed: {e}")
            print(f"❌ Discord bot start failed: {e}")
            return False

    async def send_message(self, content: str, conversation_id: str, **kwargs) -> bool:
        """Send message to Discord channel.
        
        Args:
            content: Message content
            conversation_id: Discord channel ID
            **kwargs: Additional arguments
            
        Returns:
            True if sent successfully
        """
        try:
            channel = self.bot.get_channel(int(conversation_id))
            if not channel:
                self.logger.error(f"Channel {conversation_id} not found")
                return False

            # Format as embed
            embed = format_response_as_embed(content, "Demi")
            await channel.send(embed=embed)
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Discord message: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown Discord bot gracefully."""
        try:
            self.logger.info("Discord bot shutting down...")

            # Shutdown voice client
            if self.voice_client:
                await self.voice_client.leave_all_channels()
                self.logger.info("Voice client shutdown")

            # Shutdown ramble task
            if self.ramble_task:
                self.ramble_task.stop()
                self.logger.info("Ramble task stopped")

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
        now = datetime.now()
        try:
            is_ready = self.bot.is_ready() if self.bot else False

            status = "healthy" if is_ready else "unhealthy"
            error_message = None if is_ready else "Bot not connected to Discord"

            # Record Discord bot metrics
            from src.monitoring.metrics import get_discord_metrics
            discord_metrics = get_discord_metrics()

            # Get bot latency and stats
            latency_ms = (self.bot.latency * 1000) if self.bot and is_ready else 0.0
            guild_count = len(self.bot.guilds) if self.bot else 0
            # Rough estimate of connected users
            connected_users = sum(len(guild.members) for guild in self.bot.guilds) if self.bot else 0

            discord_metrics.record_bot_status(
                online=is_ready,
                latency_ms=latency_ms,
                guild_count=guild_count,
                connected_users=connected_users
            )

            self.logger.debug("Discord health check", status=status, is_ready=is_ready)

            return PluginHealth(
                status=status,
                response_time_ms=latency_ms,
                last_check=now,
                error_message=error_message
            )

        except Exception as e:
            self.logger.error(f"Discord health check failed: {e}")
            return PluginHealth(
                status="error",
                response_time_ms=0.0,
                last_check=now,
                error_message=str(e)
            )


# For plugin discovery
PluginClass = DiscordBot
