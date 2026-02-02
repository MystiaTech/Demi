"""Discord bot integration for Demi.

Provides Discord presence, message routing, and bidirectional communication.
"""

import os
import asyncio
from typing import Optional

import discord
from discord.ext import commands

from src.platforms.base import BasePlatform, PluginHealth
from src.core.logger import get_logger
from datetime import datetime


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

    async def initialize(self, conductor) -> bool:
        """Initialize Discord bot with intents and event handlers.

        Args:
            conductor: Conductor instance for LLM routing

        Returns:
            True if initialization successful

        Raises:
            ValueError: If DISCORD_BOT_TOKEN not set or empty
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

            # Store conductor reference
            self.conductor = conductor

            # Configure intents
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message.content
            intents.guilds = True  # Required for server messages
            intents.direct_messages = True  # Required for DM handling

            # Create bot instance
            self.bot = commands.Bot(command_prefix="!", intents=intents)

            # Register event handlers
            @self.bot.event
            async def on_ready():
                """Bot connected and ready."""
                self.logger.info(
                    f"Discord bot connected as {self.bot.user}",
                    bot_id=self.bot.user.id,
                    guild_count=len(self.bot.guilds)
                )
                self._status = "online"

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
                    for mention_str in [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]:
                        content = content.replace(mention_str, "").strip()

                # Log interaction
                self.logger.info(
                    "Discord message received",
                    user_id=user_id,
                    guild_id=guild_id,
                    is_dm=is_dm,
                    content_length=len(content)
                )

                # Skip empty messages after mention removal
                if not content or len(content) == 0:
                    return

                try:
                    # Show typing indicator (improves UX)
                    async with message.channel.typing():
                        # Route through Conductor
                        response = await self.conductor.request_inference(
                            platform="discord",
                            user_id=user_id,
                            content=content,
                            context={
                                "guild_id": guild_id,
                                "channel_id": channel_id,
                                "is_dm": is_dm,
                                "author_name": str(message.author),
                                "message_timestamp": message.created_at.isoformat(),
                            }
                        )

                    # Send response (Task 3 will add formatting)
                    response_text = response.get("content", "Error generating response")
                    await message.reply(response_text, mention_author=False)

                    self.logger.info(
                        "Discord response sent",
                        user_id=user_id,
                        response_length=len(response_text)
                    )

                except Exception as e:
                    self.logger.error(
                        f"Discord message handling error: {e}",
                        user_id=user_id,
                        error_type=type(e).__name__
                    )
                    # Send error message to user
                    error_msg = "Oops, something went wrong. Try again in a moment."
                    await message.reply(error_msg, mention_author=False)

            # Log successful initialization
            self.logger.info(
                "Discord bot initialized",
                intents=["message_content", "guilds", "direct_messages"]
            )

            # Start bot in background (non-blocking)
            self._bot_task = asyncio.create_task(self.bot.start(self.token))

            self._initialized = True
            self._status = "initializing"

            return True

        except ValueError as e:
            self.logger.error(f"Discord bot configuration error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Discord bot initialization failed: {e}")
            self._status = "error"
            return False

    async def shutdown(self) -> None:
        """Shutdown Discord bot gracefully."""
        try:
            self.logger.info("Discord bot shutting down...")

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

            self.logger.debug(
                "Discord health check",
                status=status,
                is_ready=is_ready
            )

            return PluginHealth(
                status=status,
                response_time_ms=0.0,  # Discord doesn't provide latency in is_ready()
                last_check=datetime.now(),
                error_message=error_message
            )

        except Exception as e:
            self.logger.error(f"Discord health check error: {e}")
            return PluginHealth(
                status="unhealthy",
                response_time_ms=0.0,
                last_check=datetime.now(),
                error_message=str(e)
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
            "message": "Discord bot uses event-driven message routing"
        }
