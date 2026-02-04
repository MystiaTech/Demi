"""Telegram bot integration for Demi.

Provides Telegram presence, message routing, and bidirectional communication.
Integrates with Conductor's LLM pipeline and emotion system.
"""

import os
import asyncio
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatAction,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

from src.platforms.base import BasePlatform, PluginHealth
from src.core.logger import get_logger
from src.integrations.telegram_formatters import (
    escape_markdown_v2,
    format_telegram_response,
    create_emotion_keyboard,
    format_emotion_display,
    format_emotion_detail,
    format_status_message,
    format_help_message,
    format_start_message,
    should_generate_telegram_ramble,
)


class TelegramRateLimiter:
    """Rate limiter for Telegram API to prevent hitting rate limits."""

    def __init__(self, messages_per_second: float = 20):
        """Initialize rate limiter.

        Args:
            messages_per_second: Maximum messages per second (default 20)
        """
        self.messages_per_second = messages_per_second
        self.min_interval = 1.0 / messages_per_second
        self.last_send_time = 0

    async def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_send_time

        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)

        self.last_send_time = asyncio.get_event_loop().time()


class TelegramRambleTask:
    """Background task for posting spontaneous rambles on Telegram."""

    def __init__(
        self,
        application: Application,
        conductor,
        logger,
        ramble_chat_id: Optional[int] = None,
    ):
        """Initialize ramble task.

        Args:
            application: Telegram Application instance
            conductor: Conductor instance for LLM inference
            logger: Logger instance
            ramble_chat_id: Chat ID for posting rambles
        """
        self.application = application
        self.conductor = conductor
        self.logger = logger
        self.ramble_chat_id = ramble_chat_id
        self.last_ramble_time = None
        self._task = None

    async def start(self) -> None:
        """Start the ramble background task."""
        if not self.ramble_chat_id:
            self.logger.warning("TELEGRAM_RAMBLE_CHAT_ID not set - ramble posting disabled")
            return

        self._task = asyncio.create_task(self._ramble_loop())
        self.logger.info("Telegram ramble task started")

    async def stop(self) -> None:
        """Stop the ramble background task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            self.logger.info("Telegram ramble task stopped")

    async def _ramble_loop(self) -> None:
        """Main ramble loop - checks every 15 minutes for ramble triggers."""
        try:
            while True:
                await asyncio.sleep(15 * 60)  # Check every 15 minutes

                try:
                    # Get current emotion state
                    from src.emotion.persistence import EmotionPersistence

                    emotion_persist = EmotionPersistence()
                    emotion_state_obj = emotion_persist.load_latest_state()

                    # Convert to dict for decision logic
                    emotion_state = (
                        emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
                    )

                    # Check if should ramble
                    should_ramble, trigger = should_generate_telegram_ramble(
                        emotion_state, self.last_ramble_time, min_interval_minutes=60
                    )

                    if not should_ramble:
                        continue

                    self.logger.info(f"Generating Telegram ramble (trigger: {trigger})")

                    # Generate ramble content via LLM pipeline
                    prompt = self._get_ramble_prompt(trigger)
                    messages = [{"role": "user", "content": prompt}]

                    response = await self.conductor.request_inference(messages)

                    # Extract content from response
                    if isinstance(response, dict):
                        content = response.get("content", "")
                    else:
                        content = response

                    # Post to ramble chat
                    if content:
                        message = f"💭 *Random Thought:*\n\n{escape_markdown_v2(content)}"
                        await self.application.bot.send_message(
                            chat_id=self.ramble_chat_id,
                            text=message,
                            parse_mode="MarkdownV2",
                        )
                        self.logger.info(f"Ramble posted: {len(content)} chars")
                        self.last_ramble_time = datetime.now(timezone.utc)

                except Exception as e:
                    self.logger.error(f"Ramble generation failed: {e}")

        except asyncio.CancelledError:
            self.logger.debug("Ramble loop cancelled")

    def _get_ramble_prompt(self, trigger: str) -> str:
        """Get the prompt for ramble generation.

        Args:
            trigger: Trigger type ("loneliness", "excitement", "frustration")

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


class TelegramBot(BasePlatform):
    """Telegram bot platform integration.

    Routes Telegram messages to Conductor's LLM pipeline and sends responses back.
    """

    def __init__(self):
        """Initialize Telegram bot platform."""
        super().__init__()
        self._name = "telegram"
        self.application: Optional[Application] = None
        self.token: Optional[str] = None
        self.conductor = None
        self.rate_limiter = TelegramRateLimiter()
        self.ramble_task: Optional[TelegramRambleTask] = None
        self._logger = get_logger(__name__)
        self._message_handlers: Dict[str, Any] = {}
        self._user_last_message_time: Dict[int, float] = defaultdict(float)

    async def initialize(self, config: dict) -> bool:
        """Initialize Telegram bot with token and register handlers.

        Args:
            config: Configuration dictionary for Telegram platform

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not self.token:
                self._logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
                self._status = "error"
                return False

            # Create Application
            self.application = Application.builder().token(self.token).build()

            # Register handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("emotions", self._handle_emotions))
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("ramble", self._handle_ramble_command))
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
            )
            self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))

            self._status = "initialized"
            self._logger.info("Telegram bot initialized successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to initialize Telegram bot: {e}")
            self._status = "error"
            return False

    async def setup(self, conductor) -> bool:
        """Start bot and ramble loop.

        Args:
            conductor: Conductor instance for LLM inference

        Returns:
            True if setup successful, False otherwise
        """
        try:
            self.conductor = conductor

            # Start application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES
            )

            # Start ramble task
            ramble_chat_id = os.getenv("TELEGRAM_RAMBLE_CHAT_ID")
            if ramble_chat_id:
                self.ramble_task = TelegramRambleTask(
                    self.application,
                    conductor,
                    self._logger,
                    int(ramble_chat_id),
                )
                await self.ramble_task.start()

            self._status = "running"
            self._logger.info("Telegram bot started and polling")
            return True

        except Exception as e:
            self._logger.error(f"Failed to setup Telegram bot: {e}")
            self._status = "error"
            return False

    async def shutdown(self) -> None:
        """Clean shutdown of Telegram bot."""
        try:
            if self.ramble_task:
                await self.ramble_task.stop()

            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

            self._status = "offline"
            self._logger.info("Telegram bot shut down")

        except Exception as e:
            self._logger.error(f"Error during Telegram bot shutdown: {e}")

    def health_check(self) -> PluginHealth:
        """Perform health check on Telegram bot.

        Returns:
            PluginHealth object with current status
        """
        start_time = asyncio.get_event_loop().time()

        try:
            is_running = (
                self.application is not None
                and self.application.updater is not None
            )
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            return PluginHealth(
                status="healthy" if is_running else "unhealthy",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=None if is_running else "Telegram bot not running",
            )

        except Exception as e:
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            return PluginHealth(
                status="unhealthy",
                response_time_ms=response_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e),
            )

    def handle_request(self, request: dict) -> dict:
        """Handle a request from this platform.

        Args:
            request: Request dict with 'type' and other parameters

        Returns:
            Response dict with 'status' and result data
        """
        # Telegram uses event handlers, not request/response pattern
        return {"status": "error", "message": "Use event handlers instead"}

    async def send_message(
        self, content: str, chat_id: int, parse_mode: str = "MarkdownV2"
    ) -> bool:
        """Send a message through Telegram.

        Args:
            content: Message content to send
            chat_id: Telegram chat ID
            parse_mode: Parse mode for formatting (default MarkdownV2)

        Returns:
            True if sent successfully
        """
        try:
            await self.rate_limiter.wait_if_needed()
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=content,
                parse_mode=parse_mode,
            )
            return True
        except TelegramError as e:
            self._logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_notification(
        self, user_id: int, title: str, content: str
    ) -> bool:
        """Send a notification to a user.

        Args:
            user_id: Telegram user ID
            title: Notification title
            content: Notification content

        Returns:
            True if sent successfully
        """
        message = f"🔔 *{escape_markdown_v2(title)}*\n\n{escape_markdown_v2(content)}"
        return await self.send_message(message, user_id)

    # Command handlers

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        try:
            message = format_start_message()
            await update.message.reply_text(message, parse_mode="MarkdownV2")
        except Exception as e:
            self._logger.error(f"Error in /start handler: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        try:
            message = format_help_message()
            await update.message.reply_text(message, parse_mode="MarkdownV2")
        except Exception as e:
            self._logger.error(f"Error in /help handler: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

    async def _handle_emotions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /emotions command."""
        try:
            # Get current emotion state
            from src.emotion.persistence import EmotionPersistence

            emotion_persist = EmotionPersistence()
            emotion_state_obj = emotion_persist.load_latest_state()
            emotion_state = (
                emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
            )

            # Format emotion display
            message = format_emotion_display(emotion_state)

            # Create keyboard
            keyboard = create_emotion_keyboard()
            buttons = [
                [InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])
                 for btn in row]
                for row in keyboard
            ]
            reply_markup = InlineKeyboardMarkup(buttons)

            await update.message.reply_text(
                message,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )

        except Exception as e:
            self._logger.error(f"Error in /emotions handler: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        try:
            # Get conductor health
            conductor_health = (
                self.conductor.health_check()
                if self.conductor
                else {"status": "unknown"}
            )

            message = format_status_message(conductor_health, self._status)
            await update.message.reply_text(message, parse_mode="MarkdownV2")

        except Exception as e:
            self._logger.error(f"Error in /status handler: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

    async def _handle_ramble_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /ramble command to generate spontaneous thought."""
        try:
            # Show typing indicator
            await update.message.chat.send_action(ChatAction.TYPING)

            # Generate ramble
            prompt = "Generate a spontaneous thought about anything interesting right now (1-2 sentences)"
            messages = [{"role": "user", "content": prompt}]

            response = await self.conductor.request_inference(messages)

            # Extract content
            if isinstance(response, dict):
                content = response.get("content", "")
                emotion_state = response.get("emotion_state", {})
            else:
                content = response
                emotion_state = {}

            # Format response
            response_dict = {"content": content, "emotion_state": emotion_state}
            message = format_telegram_response(response_dict, update.effective_user.first_name)

            await update.message.reply_text(message, parse_mode="MarkdownV2")

        except Exception as e:
            self._logger.error(f"Error in /ramble handler: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular messages."""
        try:
            # Check if this is a private message or mention/reply in group
            if update.message.chat.type == "private":
                should_respond = True
            else:
                # In groups, only respond to mentions or replies to bot
                should_respond = (
                    self.application.bot.username in update.message.text or
                    (update.message.reply_to_message and
                     update.message.reply_to_message.from_user.id == (await self.application.bot.get_me()).id)
                )

            if not should_respond:
                return

            # Show typing indicator
            await update.message.chat.send_action(ChatAction.TYPING)

            # Extract user info
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name or "User"
            content = update.message.text
            chat_id = update.message.chat_id

            # Route through conductor
            response = await self.conductor.request_inference_for_platform(
                platform="telegram",
                user_id=str(user_id),
                user_name=user_name,
                content=content,
                platform_metadata={
                    "chat_id": chat_id,
                    "message_id": update.message.message_id,
                },
            )

            # Format and send response
            message = format_telegram_response(response, user_name)
            await update.message.reply_text(message, parse_mode="MarkdownV2")

        except Exception as e:
            self._logger.error(f"Error handling message: {e}")
            await update.message.reply_text("An error occurred. Please try again.")

    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboard buttons."""
        try:
            query = update.callback_query
            await query.answer()

            if query.data.startswith("emotion_detail_"):
                # Show emotion detail
                emotion_name = query.data.replace("emotion_detail_", "")

                from src.emotion.persistence import EmotionPersistence

                emotion_persist = EmotionPersistence()
                emotion_state_obj = emotion_persist.load_latest_state()
                emotion_state = (
                    emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
                )

                message = format_emotion_detail(emotion_name, emotion_state)
                await query.edit_message_text(
                    text=message,
                    parse_mode="MarkdownV2",
                )

            elif query.data == "refresh_emotions":
                # Refresh emotion display
                from src.emotion.persistence import EmotionPersistence

                emotion_persist = EmotionPersistence()
                emotion_state_obj = emotion_persist.load_latest_state()
                emotion_state = (
                    emotion_state_obj.get_all_emotions() if emotion_state_obj else {}
                )

                message = format_emotion_display(emotion_state)
                keyboard = create_emotion_keyboard()
                buttons = [
                    [InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"])
                     for btn in row]
                    for row in keyboard
                ]
                reply_markup = InlineKeyboardMarkup(buttons)

                await query.edit_message_text(
                    text=message,
                    parse_mode="MarkdownV2",
                    reply_markup=reply_markup,
                )

        except Exception as e:
            self._logger.error(f"Error handling callback query: {e}")
