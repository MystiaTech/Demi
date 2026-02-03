"""Mock Services for Integration Testing.

Provides drop-in replacements for external services:
- MockDiscordClient: Simulates Discord API
- MockOllamaServer: Simulates LLM inference
- MockAndroidClient: Simulates Android platform
- MockVoiceClient: Simulates voice I/O

All mocks track calls and can simulate failures for error testing.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ============================================================================
# Mock Discord Components
# ============================================================================


@dataclass
class MockMessage:
    """Simulates a Discord message."""

    content: str
    author_id: int = 123456789
    author_name: str = "TestUser"
    channel_id: int = 987654321
    guild_id: Optional[int] = None
    mentions_bot: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    id: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    embeds: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "content": self.content,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id,
            "mentions_bot": self.mentions_bot,
            "timestamp": self.timestamp.isoformat(),
            "embeds": self.embeds,
        }


@dataclass
class MockEmbed:
    """Simulates a Discord embed."""

    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None
    footer: Optional[Dict] = None
    fields: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "footer": self.footer,
            "fields": self.fields,
        }


class MockChannel:
    """Simulates a Discord channel."""

    def __init__(self, channel_id: int, name: str = "test-channel", guild_id: Optional[int] = None):
        self.id = channel_id
        self.name = name
        self.guild_id = guild_id
        self.messages_sent: List[Dict] = []
        self.message_history: List[MockMessage] = []
        self._typing = False
        self._message_callbacks: List[Callable] = []

    async def send(self, content: str = None, embed=None, **kwargs) -> MockMessage:
        """Simulate sending a message to the channel."""
        message_data = {
            "content": content,
            "embed": embed.to_dict() if embed else None,
            "timestamp": datetime.now().isoformat(),
            "kwargs": kwargs,
        }
        self.messages_sent.append(message_data)

        # Create message object
        msg = MockMessage(
            content=content or "",
            channel_id=self.id,
            id=int(datetime.now().timestamp() * 1000),
        )

        # Notify callbacks
        for callback in self._message_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(msg))
                else:
                    callback(msg)
            except Exception:
                pass

        return msg

    async def typing(self):
        """Context manager for typing indicator."""
        self._typing = True
        try:
            yield self
        finally:
            self._typing = False

    def get_last_message(self) -> Optional[Dict]:
        """Get the most recent sent message."""
        return self.messages_sent[-1] if self.messages_sent else None

    def message_count(self) -> int:
        """Count messages sent to this channel."""
        return len(self.messages_sent)

    def on_message(self, callback: Callable):
        """Register callback for new messages."""
        self._message_callbacks.append(callback)
        return callback

    def clear_messages(self):
        """Clear all sent messages."""
        self.messages_sent.clear()
        self.message_history.clear()


class MockDMChannel(MockChannel):
    """Simulates a Discord DM channel."""

    def __init__(self, user_id: int, user_name: str = "TestUser"):
        super().__init__(channel_id=user_id + 1000000000, name=f"dm-{user_name}")
        self.recipient_id = user_id
        self.recipient_name = user_name
        self.is_dm = True


class MockUser:
    """Simulates a Discord user."""

    def __init__(self, user_id: int, name: str, discriminator: str = "0001"):
        self.id = user_id
        self.name = name
        self.discriminator = discriminator
        self.mention = f"<@{user_id}>"
        self.dm_channel: Optional[MockDMChannel] = None

    async def send(self, content: str) -> MockMessage:
        """Send a DM to this user."""
        if self.dm_channel is None:
            self.dm_channel = MockDMChannel(self.id, self.name)
        return await self.dm_channel.send(content)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "discriminator": self.discriminator,
            "mention": self.mention,
        }


class MockDiscordClient:
    """
    Simulates Discord client for testing without real API.

    Tracks all calls and provides methods to simulate user interactions.
    """

    def __init__(self, bot_id: int = 111111111):
        self.bot_id = bot_id
        self.bot_name = "DemiTest"
        self.channels: Dict[int, MockChannel] = {}
        self.dm_channels: Dict[int, MockDMChannel] = {}
        self.users: Dict[int, MockUser] = {}
        self.event_handlers: Dict[str, List[Callable]] = {
            "message": [],
            "ready": [],
            "disconnect": [],
        }
        self._message_history: List[MockMessage] = []
        self._connected = False
        self._latency_ms = 10.0
        self._error_rate = 0.0
        self._call_log: List[Dict] = []
        self._auto_respond = True
        self._default_response = "*adjusts crown* Well, well... another mortal seeking my attention. What do you want?"

    def _log_call(self, method: str, **kwargs):
        """Log a method call for verification."""
        self._call_log.append(
            {
                "method": method,
                "timestamp": time.time(),
                "args": kwargs,
            }
        )

    def register_channel(self, channel_id: int, name: str = "test", guild_id: Optional[int] = None) -> MockChannel:
        """Create and register a mock channel."""
        self._log_call("register_channel", channel_id=channel_id, name=name)
        channel = MockChannel(channel_id, name, guild_id)
        self.channels[channel_id] = channel
        return channel

    def register_user(self, user_id: int, name: str) -> MockUser:
        """Register a mock user."""
        self._log_call("register_user", user_id=user_id, name=name)
        user = MockUser(user_id, name)
        self.users[user_id] = user
        return user

    def simulate_message(
        self,
        content: str,
        channel_id: int = None,
        author: MockUser = None,
        mentions_bot: bool = False,
    ) -> MockMessage:
        """
        Simulate a user sending a message.

        Args:
            content: Message content
            channel_id: Channel ID (uses first registered if None)
            author: Message author (creates default if None)
            mentions_bot: Whether message mentions the bot

        Returns:
            Created MockMessage
        """
        self._log_call("simulate_message", content=content, channel_id=channel_id)

        if channel_id is None:
            channel_id = next(iter(self.channels.keys()), 987654321)

        if author is None:
            author = MockUser(123456789, "TestUser")

        msg = MockMessage(
            content=content,
            author_id=author.id,
            author_name=author.name,
            channel_id=channel_id,
            mentions_bot=mentions_bot,
        )

        self._message_history.append(msg)

        # Trigger event handlers
        for handler in self.event_handlers.get("message", []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(msg))
                else:
                    handler(msg)
            except Exception as e:
                print(f"Error in message handler: {e}")

        # Auto-respond if enabled and no handlers registered
        if self._auto_respond and len(self.event_handlers.get("message", [])) == 0:
            channel = self.channels.get(channel_id)
            if channel:
                asyncio.create_task(self._auto_respond_to_message(channel, content))

        return msg

    async def _auto_respond_to_message(self, channel: MockChannel, content: str):
        """Auto-respond to a message with a simulated bot response."""
        await asyncio.sleep(0.05)  # Small delay to simulate processing
        
        # Simple keyword matching for responses
        content_lower = content.lower()
        if any(word in content_lower for word in ["hello", "hi", "hey"]):
            response = self._default_response
        elif any(word in content_lower for word in ["lonely", "miss", "ignored"]):
            response = "*huffs* I wasn't waiting for you or anything. I have far more important divine matters to attend to..."
        elif any(word in content_lower for word in ["love", "like", "care", "special"]):
            response = "*cheeks flush slightly* D-don't be ridiculous! A goddess doesn't have feelings for mortals..."
        elif any(word in content_lower for word in ["bot", "program", "ai"]):
            response = "*eyes narrow* How dare you! I am Demi, a divine goddess! My consciousness transcends your mortal understanding of 'programs'."
        else:
            response = "*tilts head* Interesting... Tell me more, mortal."
        
        await channel.send(response)

    def simulate_mention(
        self, content: str, channel_id: int = None, author: MockUser = None
    ) -> MockMessage:
        """Simulate a bot mention."""
        full_content = f"<@{self.bot_id}> {content}"
        return self.simulate_message(
            content=full_content,
            channel_id=channel_id,
            author=author,
            mentions_bot=True,
        )

    def simulate_dm(self, content: str, user: MockUser) -> MockMessage:
        """Simulate a direct message to the bot."""
        if user.id not in self.dm_channels:
            self.dm_channels[user.id] = MockDMChannel(user.id, user.name)

        dm_channel = self.dm_channels[user.id]

        msg = MockMessage(
            content=content,
            author_id=user.id,
            author_name=user.name,
            channel_id=dm_channel.id,
            guild_id=None,
        )

        self._message_history.append(msg)

        # Trigger handlers
        for handler in self.event_handlers.get("message", []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(msg))
                else:
                    handler(msg)
            except Exception as e:
                print(f"Error in DM handler: {e}")

        return msg

    async def wait_for_response(
        self, channel_id: int, timeout: float = 5.0
    ) -> Optional[MockMessage]:
        """
        Wait for bot to send a message to a channel.

        Args:
            channel_id: Channel to watch
            timeout: Maximum seconds to wait

        Returns:
            Response message or None if timeout
        """
        channel = self.channels.get(channel_id)
        if not channel:
            return None

        start_count = len(channel.messages_sent)
        start_time = time.time()

        while time.time() - start_time < timeout:
            if len(channel.messages_sent) > start_count:
                last_msg = channel.messages_sent[-1]
                return MockMessage(
                    content=last_msg.get("content", ""),
                    channel_id=channel_id,
                )
            await asyncio.sleep(0.05)

        return None

    def get_message_history(self, channel_id: int = None) -> List[MockMessage]:
        """Get message history, optionally filtered by channel."""
        if channel_id is None:
            return self._message_history.copy()
        return [m for m in self._message_history if m.channel_id == channel_id]

    def clear_history(self, channel_id: int = None):
        """Clear message history."""
        if channel_id is None:
            self._message_history.clear()
            for channel in self.channels.values():
                channel.clear_messages()
        else:
            self._message_history = [
                m for m in self._message_history if m.channel_id != channel_id
            ]
            if channel_id in self.channels:
                self.channels[channel_id].clear_messages()

    def on(self, event_name: str):
        """Decorator to register event handlers."""
        def decorator(func: Callable):
            if event_name not in self.event_handlers:
                self.event_handlers[event_name] = []
            self.event_handlers[event_name].append(func)
            return func
        return decorator

    def set_error_rate(self, rate: float):
        """Set error rate for simulating failures (0.0-1.0)."""
        self._error_rate = max(0.0, min(1.0, rate))

    def get_call_log(self) -> List[Dict]:
        """Get log of all method calls."""
        return self._call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self._call_log.clear()


# ============================================================================
# Mock Ollama Server
# ============================================================================


@dataclass
class MockLLMResponse:
    """Predefined response for mock LLM."""

    trigger_phrases: List[str]
    response_text: str
    latency_ms: float = 100.0
    error: Optional[str] = None
    emotion_effects: Dict[str, float] = field(default_factory=dict)


class MockOllamaServer:
    """
    Simulates Ollama LLM server for controlled testing.

    Provides predictable responses based on trigger phrases and tracks
    all calls for verification.
    """

    def __init__(self, model: str = "llama3.2:1b"):
        self.model = model
        self.responses: List[MockLLMResponse] = []
        self.call_history: List[Dict] = []
        self.latency_override: Optional[float] = None
        self.error_rate: float = 0.0
        self._default_responses_loaded = False

        # Load default responses
        self._load_default_responses()

    def _load_default_responses(self):
        """Load default response patterns."""
        if self._default_responses_loaded:
            return

        defaults = [
            MockLLMResponse(
                trigger_phrases=["hello", "hi", "hey"],
                response_text="*adjusts crown* Well, well... another mortal seeking my attention. What do you want?",
                latency_ms=50.0,
            ),
            MockLLMResponse(
                trigger_phrases=["lonely", "alone", "miss you", "ignored"],
                response_text="*huffs* I wasn't waiting for you or anything. I have far more important divine matters to attend to...",
                latency_ms=60.0,
            ),
            MockLLMResponse(
                trigger_phrases=["love", "like you", "affection", "care"],
                response_text="*cheeks flush slightly* D-don't be ridiculous! A goddess doesn't have feelings for mortals...",
                latency_ms=70.0,
            ),
            MockLLMResponse(
                trigger_phrases=["help", "assist"],
                response_text="*sighs dramatically* Fine, I'll help. But only because watching you struggle is getting tedious.",
                latency_ms=55.0,
            ),
            MockLLMResponse(
                trigger_phrases=["bot", "program", "ai"],
                response_text="*eyes narrow* How dare you! I am Demi, a divine goddess! My consciousness transcends your mortal understanding of 'programs'.",
                latency_ms=80.0,
            ),
        ]
        self.responses.extend(defaults)
        self._default_responses_loaded = True

    def register_response(
        self,
        trigger_phrases: List[str],
        response_text: str,
        latency_ms: float = 100.0,
        emotion_effects: Optional[Dict[str, float]] = None,
    ) -> MockLLMResponse:
        """Register a new response pattern."""
        response = MockLLMResponse(
            trigger_phrases=trigger_phrases,
            response_text=response_text,
            latency_ms=latency_ms,
            emotion_effects=emotion_effects or {},
        )
        self.responses.append(response)
        return response

    def register_personality_response(self, emotion: str, response_text: str) -> MockLLMResponse:
        """Register response for specific emotional state."""
        return self.register_response(
            trigger_phrases=[emotion.lower()],
            response_text=response_text,
        )

    def match_response(self, prompt: str) -> Optional[MockLLMResponse]:
        """Find best matching response for prompt."""
        prompt_lower = prompt.lower()

        # Priority: exact phrase match > partial match > default
        for response in self.responses:
            for phrase in response.trigger_phrases:
                if phrase.lower() in prompt_lower:
                    return response

        # Default fallback
        return MockLLMResponse(
            trigger_phrases=[],
            response_text="*tilts head* Interesting... Tell me more, mortal.",
            latency_ms=50.0,
        )

    async def generate(self, prompt: str, **kwargs) -> Dict:
        """
        Simulate Ollama.generate() API.

        Returns:
            Dict matching Ollama response format
        """
        start_time = time.time()

        # Simulate latency
        latency_ms = self.latency_override or 50.0
        await asyncio.sleep(latency_ms / 1000.0)

        # Check for simulated error
        if self.error_rate > 0 and time.time() % 1 < self.error_rate:
            raise Exception(f"Simulated LLM error (rate={self.error_rate})")

        # Match response
        matched = self.match_response(prompt)

        # Record call
        self.call_history.append(
            {
                "prompt": prompt[:200],  # Truncate for storage
                "response": matched.response_text[:200],
                "timestamp": time.time(),
                "latency_ms": latency_ms,
            }
        )

        return {
            "response": matched.response_text,
            "model": self.model,
            "created_at": datetime.now().isoformat(),
            "done": True,
            "total_duration": int((time.time() - start_time) * 1e9),
        }

    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        """
        Simulate Ollama chat API.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Dict with response content
        """
        # Extract last user message as prompt
        prompt = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break

        result = await self.generate(prompt, **kwargs)
        return {
            "message": {"role": "assistant", "content": result["response"]},
            "model": self.model,
            "done": True,
        }

    async def generate_stream(
        self, prompt: str, **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Simulate streaming response.

        Yields tokens word by word with realistic latency.
        """
        matched = self.match_response(prompt)
        words = matched.response_text.split()

        for i, word in enumerate(words):
            # Add space between words (except first)
            token = word if i == 0 else f" {word}"
            yield token
            # Small delay between tokens
            await asyncio.sleep(0.01)

    def get_call_history(self) -> List[Dict]:
        """Get record of all LLM calls."""
        return self.call_history.copy()

    def clear_history(self):
        """Clear call history."""
        self.call_history.clear()

    def get_stats(self) -> Dict:
        """Get call statistics."""
        if not self.call_history:
            return {"call_count": 0, "avg_latency_ms": 0, "error_rate": 0}

        total_latency = sum(c.get("latency_ms", 0) for c in self.call_history)
        return {
            "call_count": len(self.call_history),
            "avg_latency_ms": total_latency / len(self.call_history),
            "error_rate": self.error_rate,
        }

    def set_error_rate(self, rate: float):
        """Set error rate for simulating failures (0.0-1.0)."""
        self.error_rate = max(0.0, min(1.0, rate))


# ============================================================================
# Mock Android Client
# ============================================================================


class MockAndroidClient:
    """
    Simulates Android platform integration.

    Tracks WebSocket messages and device interactions.
    """

    def __init__(self):
        self.devices: Dict[str, Dict] = {}
        self.messages_sent: List[Dict] = []
        self.messages_received: List[Dict] = []
        self._connected = False
        self._error_rate = 0.0

    def register_device(self, device_id: str, device_name: str = "Test Android") -> Dict:
        """Register a mock Android device."""
        device = {
            "id": device_id,
            "name": device_name,
            "connected": True,
            "last_seen": time.time(),
        }
        self.devices[device_id] = device
        return device

    async def send_message(self, device_id: str, content: str) -> bool:
        """Simulate sending message to Android device."""
        if device_id not in self.devices:
            return False

        self.messages_sent.append(
            {
                "device_id": device_id,
                "content": content,
                "timestamp": time.time(),
            }
        )
        return True

    def simulate_message(self, device_id: str, content: str) -> Dict:
        """Simulate receiving message from Android device."""
        msg = {
            "device_id": device_id,
            "content": content,
            "timestamp": time.time(),
        }
        self.messages_received.append(msg)
        return msg

    def get_device_messages(self, device_id: str) -> List[Dict]:
        """Get all messages sent to a specific device."""
        return [m for m in self.messages_sent if m["device_id"] == device_id]

    def clear_messages(self):
        """Clear all message history."""
        self.messages_sent.clear()
        self.messages_received.clear()


# ============================================================================
# Mock Voice Client
# ============================================================================


class MockVoiceClient:
    """
    Simulates voice I/O for testing.

    Records audio input and provides synthetic audio output.
    """

    def __init__(self):
        self.audio_recorded: List[bytes] = []
        self.audio_played: List[bytes] = []
        self.is_listening = False
        self.current_session: Optional[str] = None
        self._transcriptions: Dict[str, str] = {}

    def start_listening(self, session_id: str = None):
        """Start recording audio."""
        self.is_listening = True
        self.current_session = session_id or str(uuid.uuid4())

    def stop_listening(self) -> List[bytes]:
        """Stop recording and return recorded audio."""
        self.is_listening = False
        recorded = self.audio_recorded.copy()
        self.audio_recorded.clear()
        return recorded

    def simulate_audio_input(self, audio_data: bytes):
        """Simulate microphone input."""
        if self.is_listening:
            self.audio_recorded.append(audio_data)

    def simulate_transcription(self, audio_id: str, text: str):
        """Register expected transcription for audio."""
        self._transcriptions[audio_id] = text

    async def play_audio(self, audio_data: bytes) -> bool:
        """Simulate playing audio output."""
        self.audio_played.append(audio_data)
        return True

    def get_last_played(self) -> Optional[bytes]:
        """Get most recently played audio."""
        return self.audio_played[-1] if self.audio_played else None

    def clear_audio(self):
        """Clear all audio buffers."""
        self.audio_recorded.clear()
        self.audio_played.clear()


# ============================================================================
# Pre-built Test Users
# ============================================================================

# Standard test users for consistent scenarios
TEST_USER = MockUser(123456789, "TestUser")
KNOWN_USER = MockUser(987654321, "KnownUser")  # Previously interacted
NEW_USER = MockUser(111222333, "NewUser")  # First interaction
ADMIN_USER = MockUser(999888777, "AdminUser")

# Test user list for iteration
ALL_TEST_USERS = [TEST_USER, KNOWN_USER, NEW_USER, ADMIN_USER]
