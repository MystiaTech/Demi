"""Discord voice integration for Demi.

Provides voice channel connectivity, wake word detection, and bidirectional
voice I/O through STT/TTS pipeline integration.

Required System Dependencies:
    - FFmpeg (for audio playback)
    - libopus (for voice encoding/decoding)

Environment Variables:
    DISCORD_VOICE_ENABLED: Enable voice features (default: "false")
    DISCORD_WAKE_WORD: Wake word to activate (default: "Demi")
    DISCORD_VOICE_TIMEOUT_SEC: Seconds of silence before leaving (default: 300)
"""

import os
import asyncio
import audioop
import io
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Callable
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from src.core.logger import get_logger

# Import voice components (may be implemented in parallel)
try:
    from src.voice.stt import SpeechToText, TranscriptionResult
    HAS_STT = True
except ImportError:
    HAS_STT = False
    SpeechToText = None
    TranscriptionResult = None

try:
    from src.voice.tts import TextToSpeech
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    TextToSpeech = None

try:
    from src.voice.vad import VoiceActivityDetector
    HAS_VAD = True
except ImportError:
    HAS_VAD = False
    VoiceActivityDetector = None

try:
    from src.models.emotional_state import EmotionalState
    HAS_EMOTIONAL_STATE = True
except ImportError:
    HAS_EMOTIONAL_STATE = False
    EmotionalState = None

# Voice transcript logging
from src.integrations.voice_transcript_logger import get_voice_logger
from src.integrations.voice_safety import get_voice_safety_guard

# Voice receive support - discord.py experimental
try:
    import discord.sinks
    HAS_VOICE_RECEIVE = True
except ImportError:
    HAS_VOICE_RECEIVE = False

# Try alternative imports for voice receive
try:
    from discord.sinks import Sink, MP3Sink
    HAS_SINK = True
except ImportError:
    HAS_SINK = False
    Sink = None
    MP3Sink = None


class STTSink(discord.sinks.Sink if HAS_VOICE_RECEIVE else object):
    """Custom audio sink for Speech-to-Text processing.
    
    Receives audio data from Discord voice receive and processes it
    through STT pipeline.
    """
    
    def __init__(self, voice_client: "DiscordVoiceClient", guild_id: int, *, filters=None):
        super().__init__(filters=filters)
        self.voice_client = voice_client
        self.guild_id = guild_id
        self.logger = get_logger()
        self.audio_data: Dict[int, bytes] = {}
        self._loop = asyncio.get_event_loop()
        
    def write(self, data: bytes, user_id: int):
        """Called when audio data is received from a user.
        
        Args:
            data: Raw audio data
            user_id: Discord user ID (int)
        """
        # Ignore bot's own voice
        if user_id == self.voice_client.bot.user.id:
            return
            
        if user_id not in self.audio_data:
            self.audio_data[user_id] = b""
        self.audio_data[user_id] += data
        
        # Process audio for this user (use threadsafe since called from DecodeManager thread)
        asyncio.run_coroutine_threadsafe(self._process_user_audio(user_id), self._loop)
        
    async def _process_user_audio(self, user_id: int):
        """Process accumulated audio for a user.
        
        Args:
            user_id: Discord user ID
        """
        if user_id not in self.audio_data:
            return
            
        audio = self.audio_data[user_id]
        if len(audio) < 16000 * 2 * 1:  # At least 1 second of audio
            return
            
        # Clear buffer
        self.audio_data[user_id] = b""
        
        # Get user info from bot
        user = self.voice_client.bot.get_user(user_id)
        username = user.name if user else f"User_{user_id}"
        
        # Process through voice client
        await self.voice_client._handle_incoming_audio(
            self.guild_id, user_id, username, audio
        )
        
    def cleanup(self):
        """Cleanup when recording stops."""
        self.audio_data.clear()


@dataclass
class VoiceSession:
    """Active voice session state.
    
    Attributes:
        voice_client: Discord voice client instance
        channel_id: Discord channel ID
        guild_id: Discord guild ID
        start_time: When session started
        last_activity: Last time audio was received
        is_listening: Whether currently listening for commands
        is_speaking: Whether currently speaking/playing audio
        wake_word_detected: Whether wake word has been detected
        pending_audio_buffer: Accumulated audio data for processing
        user_speaking_start: When current user started speaking
        current_user_id: ID of user currently speaking
        session_id: Unique session identifier for logging
    """
    voice_client: discord.VoiceClient
    channel_id: int
    guild_id: int
    start_time: datetime
    last_activity: datetime
    is_listening: bool = True
    is_speaking: bool = False
    wake_word_detected: bool = False
    pending_audio_buffer: bytes = field(default_factory=bytes)
    user_speaking_start: Optional[datetime] = None
    current_user_id: Optional[int] = None
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))


class AudioBuffer:
    """Thread-safe audio buffer for voice data."""
    
    def __init__(self, max_size: int = 16000 * 2 * 10):  # 10 seconds at 16kHz
        self._buffer = b""
        self._lock = threading.Lock()
        self.max_size = max_size
        self.user_id: Optional[int] = None
        self.speech_start: Optional[datetime] = None
    
    def append(self, data: bytes, user_id: int) -> bool:
        """Append audio data to buffer.
        
        Returns:
            True if this is new speech (speech_start was None)
        """
        with self._lock:
            is_new_speech = self.speech_start is None
            if is_new_speech:
                self.speech_start = datetime.now()
                self.user_id = user_id
            
            self._buffer += data
            
            # Trim if exceeds max size
            if len(self._buffer) > self.max_size:
                self._buffer = self._buffer[-self.max_size:]
            
            return is_new_speech
    
    def get_and_clear(self) -> tuple[bytes, int]:
        """Get buffer contents and clear.
        
        Returns:
            Tuple of (audio_data, user_id)
        """
        with self._lock:
            data = self._buffer
            user_id = self.user_id or 0
            self._buffer = b""
            self.speech_start = None
            self.user_id = None
            return data, user_id
    
    def clear(self):
        """Clear buffer."""
        with self._lock:
            self._buffer = b""
            self.speech_start = None
            self.user_id = None
    
    @property
    def duration_ms(self) -> float:
        """Get duration of buffered audio in milliseconds."""
        # 16kHz, 16-bit = 32000 bytes per second
        return (len(self._buffer) / 32000) * 1000
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


class DiscordVoiceClient:
    """Discord voice client managing voice channel connections and audio I/O.
    
    Provides voice channel connection, wake word detection ("Demi"),
    continuous audio listening with VAD, and STT/TTS pipeline integration.
    
    The voice pipeline works as follows:
    1. Discord Voice Client receives Opus audio
    2. Opus → PCM decode
    3. VAD (Voice Activity Detection)
    4. STT (Speech-to-Text)
    5. Wake word "Demi" detection
    6. LLM Pipeline (via Conductor)
    7. TTS (Text-to-Speech)
    8. Discord Voice Client playback
    
    Attributes:
        bot: Discord bot instance
        conductor: Conductor instance for LLM access
        sessions: Dict mapping guild_id to VoiceSession
        wake_word: Wake word to activate listening (default: "Demi")
        voice_timeout_sec: Seconds of inactivity before auto-leave
        listen_after_response: Always-listening mode flag
    """
    
    def __init__(self, bot: commands.Bot, conductor):
        """Initialize Discord voice client.
        
        Args:
            bot: Discord bot instance
            conductor: Conductor instance for LLM access
        """
        self.bot = bot
        self.conductor = conductor
        self.logger = get_logger()
        
        # Initialize voice components if available
        if HAS_STT:
            self.stt = SpeechToText()
        else:
            self.stt = None
            self.logger.warning("STT not available - voice transcription disabled")
            
        if HAS_TTS:
            self.tts = TextToSpeech()
        else:
            self.tts = None
            self.logger.warning("TTS not available - voice synthesis disabled")
            
        if HAS_VAD:
            self.vad = VoiceActivityDetector()
        else:
            self.vad = None
            self.logger.warning("VAD not available - speech detection may be impaired")
        
        # Active voice sessions by guild_id
        self.sessions: Dict[int, VoiceSession] = {}
        
        # Audio buffers per guild
        self._audio_buffers: Dict[int, AudioBuffer] = {}
        
        # Configuration
        self.wake_word = os.getenv("DISCORD_WAKE_WORD", "Demi")
        self.voice_timeout_sec = int(os.getenv("DISCORD_VOICE_TIMEOUT_SEC", "300"))
        self.listen_after_response = True  # Always-listening mode
        
        # Opus decoder (initialized lazily)
        self._opus_decoder = None
        
        # Running tasks for cleanup
        self._listen_tasks: Dict[int, asyncio.Task] = {}
        
        # Voice recording sinks per guild
        self._voice_sinks: Dict[int, STTSink] = {}
        
        # Transcript logger
        self.transcript_logger = get_voice_logger()
        
        # Safety guard (bot user ID set when bot connects)
        self.safety_guard = get_voice_safety_guard(bot_user_id=None)
        self._bot_user_id: Optional[int] = None
        
        self.logger.info(
            "DiscordVoiceClient initialized",
            wake_word=self.wake_word,
            timeout_sec=self.voice_timeout_sec,
            stt_available=HAS_STT,
            tts_available=HAS_TTS,
            vad_available=HAS_VAD,
            voice_receive_available=HAS_VOICE_RECEIVE,
        )
    
    async def join_channel(self, channel: discord.VoiceChannel) -> bool:
        """Connect to a voice channel.
        
        Args:
            channel: Discord voice channel to join
            
        Returns:
            True if connection successful
        """
        try:
            guild_id = channel.guild.id
            
            # Check if already connected to this guild
            if guild_id in self.sessions:
                existing_session = self.sessions[guild_id]
                if existing_session.voice_client.is_connected():
                    self.logger.info(f"Already connected to voice channel in guild {guild_id}")
                    return True
            
            self.logger.info(f"Connecting to voice channel: {channel.name}")
            
            # Connect to voice channel
            voice_client = await channel.connect()
            
            # Create session
            now = datetime.now()
            session = VoiceSession(
                voice_client=voice_client,
                channel_id=channel.id,
                guild_id=guild_id,
                start_time=now,
                last_activity=now,
                is_listening=True,
            )
            
            self.sessions[guild_id] = session
            self._audio_buffers[guild_id] = AudioBuffer()
            
            # Start voice listening
            await self._on_voice_connect(voice_client)
            
            return True
            
        except discord.errors.ClientException as e:
            self.logger.error(f"Discord client error joining voice channel: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to join voice channel: {type(e).__name__}: {e}")
            return False
    
    async def leave_channel(self, guild_id: int) -> bool:
        """Disconnect from a voice channel.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if was connected and disconnected
        """
        session = self.sessions.get(guild_id)
        
        if not session:
            self.logger.debug(f"No active session for guild {guild_id}")
            return False
        
        try:
            voice_client = session.voice_client
            
            # Cancel listening task
            if guild_id in self._listen_tasks:
                self._listen_tasks[guild_id].cancel()
                try:
                    await self._listen_tasks[guild_id]
                except asyncio.CancelledError:
                    pass
                del self._listen_tasks[guild_id]
            
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
                self.logger.info(f"Disconnected from voice channel in guild {guild_id}")
            
            # Clean up session
            await self._on_voice_disconnect(guild_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error leaving voice channel: {e}")
            return False
    
    async def leave_all_channels(self):
        """Disconnect from all voice channels (shutdown cleanup)."""
        self.logger.info("Leaving all voice channels...")
        
        # Copy keys since we'll be modifying the dict
        guild_ids = list(self.sessions.keys())
        
        for guild_id in guild_ids:
            await self.leave_channel(guild_id)
        
        self.logger.info("All voice channels disconnected")
    
    def is_connected_to(self, guild_id: int) -> bool:
        """Check if connected to a guild's voice channel.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if connected to voice channel in guild
        """
        session = self.sessions.get(guild_id)
        if not session:
            return False
        return session.voice_client.is_connected()
    
    def get_session(self, guild_id: int) -> Optional[VoiceSession]:
        """Get active voice session for guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            VoiceSession if active, None otherwise
        """
        return self.sessions.get(guild_id)
    
    def start_listening(self, guild_id: int) -> bool:
        """Enable always-listening mode for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if session found and listening enabled
        """
        session = self.sessions.get(guild_id)
        if session:
            session.is_listening = True
            self.listen_after_response = True
            self.logger.info(f"Started listening in guild {guild_id}")
            return True
        return False
    
    def stop_listening(self, guild_id: int) -> bool:
        """Disable always-listening mode (wake-word only).
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if session found and listening disabled
        """
        session = self.sessions.get(guild_id)
        if session:
            session.is_listening = False
            self.listen_after_response = False
            self.logger.info(f"Stopped listening in guild {guild_id}")
            return True
        return False
    
    async def play_audio(self, guild_id: int, audio_path: str) -> bool:
        """Play audio file in voice channel.
        
        Args:
            guild_id: Discord guild ID
            audio_path: Path to audio file to play
            
        Returns:
            True if audio started playing
        """
        session = self.sessions.get(guild_id)
        if not session or not session.voice_client.is_connected():
            self.logger.error(f"Not connected to voice channel in guild {guild_id}")
            return False
        
        return await self._speak_in_channel(session.voice_client, audio_path)
    
    async def _on_voice_connect(self, voice_client: discord.VoiceClient):
        """Called when successfully connected to voice channel.
        
        Args:
            voice_client: Discord voice client instance
        """
        guild_id = voice_client.guild.id
        channel_name = voice_client.channel.name
        self.logger.info(f"Connected to voice channel: {channel_name}", guild_id=guild_id)
        
        # Set bot user ID for safety guard
        if self.bot and self.bot.user and not self._bot_user_id:
            self._bot_user_id = self.bot.user.id
            self.safety_guard.bot_user_id = self._bot_user_id
        
        # Start voice recording if available
        if HAS_VOICE_RECEIVE:
            try:
                sink = STTSink(self, guild_id)
                self._voice_sinks[guild_id] = sink
                voice_client.start_recording(sink, self._on_recording_finished)
                self.logger.info(f"Voice recording started for guild {guild_id}")
            except Exception as e:
                self.logger.error(f"Failed to start voice recording: {e}")
        else:
            self.logger.warning(
                "Voice receive not available. Demi cannot hear users. "
                "Install discord.py with voice receive support."
            )
        
        # Play join sound
        await self._play_join_sound(voice_client)
        
        # Start listening loop for session management
        task = asyncio.create_task(self._voice_listen_loop(voice_client))
        self._listen_tasks[guild_id] = task
    
    def _on_recording_finished(self, sink: STTSink, *args):
        """Called when voice recording stops.
        
        Args:
            sink: The audio sink that was recording
        """
        self.logger.info(f"Voice recording finished for guild")
        sink.cleanup()
    
    async def _on_voice_disconnect(self, guild_id: int):
        """Called when disconnected from voice channel.
        
        Args:
            guild_id: Discord guild ID
        """
        self.logger.info(f"Disconnected from voice channel in guild {guild_id}")
        
        # Clean up session
        if guild_id in self.sessions:
            del self.sessions[guild_id]
        
        # Clean up audio buffer
        if guild_id in self._audio_buffers:
            del self._audio_buffers[guild_id]
    
    async def _voice_listen_loop(self, voice_client: discord.VoiceClient):
        """Main listening loop for voice channel.
        
        Note: discord.py doesn't support receiving audio in the standard library.
        This is a placeholder that implements the structure. For actual audio
        receiving, you would need to use discord.py's experimental voice receive
        or a fork that supports it.
        
        Args:
            voice_client: Discord voice client instance
        """
        guild_id = voice_client.guild.id
        session = self.sessions.get(guild_id)
        
        if not session:
            self.logger.error(f"No session found for guild {guild_id}")
            return
        
        self.logger.info(f"Voice listen loop started for guild {guild_id}")
        self.logger.info(
            "Note: discord.py voice receive requires experimental features. "
            "Install discord.py[voice]>=2.5.0 and ensure FFmpeg is available."
        )
        
        # Note: Standard discord.py doesn't expose audio receiving easily.
        # The voice receive API is available through:
        # 1. discord.py 2.5+ with voice receive support (experimental)
        # 2. Forks like pycord or nextcord
        # 3. Custom voice client implementation
        
        # For now, we implement the session management loop
        while voice_client.is_connected() and session.is_listening:
            try:
                # Check for timeout
                if self._should_timeout(session):
                    self.logger.info("Voice session timeout, leaving channel")
                    await self.leave_channel(guild_id)
                    break
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                self.logger.debug(f"Listen loop cancelled for guild {guild_id}")
                break
            except Exception as e:
                self.logger.error(f"Voice listen loop error: {e}")
                await asyncio.sleep(1)
        
        self.logger.info(f"Voice listen loop ended for guild {guild_id}")
    
    async def _process_audio_packet(
        self, 
        guild_id: int, 
        user_id: int, 
        audio_data: bytes
    ):
        """Process received audio packet from user.
        
        This method should be called by the voice receive implementation
        when audio packets are received from users.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            audio_data: Raw Opus audio packet
        """
        # Ignore bot's own audio
        if user_id == self.bot.user.id:
            return
        
        session = self.sessions.get(guild_id)
        if not session or not session.is_listening:
            return
        
        # Skip if STT not available
        if not HAS_STT or not self.stt:
            return
        
        try:
            # Convert Discord Opus to PCM
            pcm_data = self._opus_to_pcm(audio_data)
            
            if not pcm_data:
                return
            
            # Get or create audio buffer for guild
            buffer = self._audio_buffers.get(guild_id)
            if not buffer:
                return
            
            # Add to buffer
            is_new_speech = buffer.append(pcm_data, user_id)
            
            if is_new_speech:
                session.last_activity = datetime.now()
            
            # Run VAD on latest frame if available
            if HAS_VAD and self.vad:
                is_speech = self._detect_speech(pcm_data)
                
                if is_speech:
                    session.last_activity = datetime.now()
                else:
                    # Speech ended - process buffer
                    if buffer.speech_start and buffer.duration_ms > 500:
                        await self._process_utterance(session, buffer)
                        
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
    
    async def _handle_incoming_audio(
        self,
        guild_id: int,
        user_id: int,
        username: str,
        audio_data: bytes
    ):
        """Handle incoming audio from voice receive sink.
        
        This is called by the STTSink when audio is received.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            username: Discord username
            audio_data: Raw audio data (Opus)
        """
        session = self.sessions.get(guild_id)
        if not session or not session.is_listening:
            return
        
        # Convert Opus to PCM
        pcm_data = self._opus_to_pcm(audio_data)
        if not pcm_data:
            return
        
        # Add to buffer
        buffer = self._audio_buffers.get(guild_id)
        if not buffer:
            return
        
        is_new_speech = buffer.append(pcm_data, user_id)
        
        # Update session activity
        session.last_activity = datetime.now()
        
        # Check if we should process (enough audio accumulated)
        if buffer.duration_ms >= 2000:  # 2 seconds of audio
            await self._process_audio_buffer(session, buffer, user_id, username)
    
    async def _process_audio_buffer(
        self,
        session: VoiceSession,
        buffer: AudioBuffer,
        user_id: int,
        username: str
    ):
        """Process audio buffer and transcribe.
        
        Args:
            session: Active voice session
            buffer: Audio buffer
            user_id: Discord user ID
            username: Discord username
        """
        audio_data, _ = buffer.get_and_clear()
        
        if len(audio_data) < 6400:  # Min 200ms
            return
        
        # Transcribe
        transcription = await self._transcribe_audio(audio_data)
        if not transcription or not transcription.text:
            return
        
        text = transcription.text.strip()
        if not text:
            return
        
        # Log user speech
        self.transcript_logger.log_user_speech(
            text=text,
            guild_id=session.guild_id,
            channel_id=session.channel_id,
            user_id=user_id,
            username=username,
            session_id=session.session_id
        )
        
        self.logger.info(f"[VOICE] {username}: {text}")
        
        # Process command
        await self._process_utterance_text(session, user_id, username, text)
    
    async def _process_utterance_text(
        self,
        session: VoiceSession,
        user_id: int,
        username: str,
        text: str
    ):
        """Process transcribed text utterance with safety checks.
        
        Args:
            session: Active voice session
            user_id: Discord user ID
            username: Discord username
            text: Transcribed text
        """
        # Safety check first
        allowed, reason = self.safety_guard.check_safety(
            user_id=user_id,
            username=username,
            text=text,
            guild_id=session.guild_id
        )
        
        if not allowed:
            self.logger.warning(f"[SAFETY] Blocked voice input from {username}: {reason}")
            return
        
        # Check for wake word (unless in always-listening mode)
        if not session.wake_word_detected and not self.listen_after_response:
            if self._check_wake_word(text):
                self.logger.info(f"Wake word detected from {username}")
                session.wake_word_detected = True
                await self._play_wake_acknowledgment(session.voice_client)
                
                # If only wake word, wait for more
                if len(text.split()) <= 2:
                    return
            else:
                # No wake word and not always-listening
                return
        
        # Record this activation passed safety checks
        self.safety_guard.record_activation(user_id)
        
        # Get response from Conductor
        response_text = await self._get_llm_response(username, text)
        
        # Log Demi's response
        self.transcript_logger.log_demi_response(
            text=response_text,
            guild_id=session.guild_id,
            channel_id=session.channel_id,
            session_id=session.session_id
        )
        
        # Speak response
        await self._speak_response_text(session.voice_client, response_text)
        
        # Reset wake word detection
        if not self.listen_after_response:
            session.wake_word_detected = False
    
    async def _get_llm_response(self, username: str, text: str) -> str:
        """Get response from LLM via Conductor.
        
        Args:
            username: User's name
            text: User's message
            
        Returns:
            Response text
        """
        if not self.conductor:
            return "I'm not connected to my brain right now."
        
        try:
            messages = [{
                "role": "user",
                "content": f"[Voice from {username}] {text}"
            }]
            
            response = await self.conductor.request_inference(messages)
            
            if isinstance(response, dict):
                return response.get("content", "")
            return response
            
        except Exception as e:
            self.logger.error(f"LLM error: {e}")
            return "I'm sorry, I couldn't process that."
    
    async def _speak_response_text(
        self, 
        voice_client: discord.VoiceClient, 
        text: str,
        guild_id: int = None
    ):
        """Speak text via TTS with safety tracking.
        
        Args:
            voice_client: Discord voice client
            text: Text to speak
            guild_id: Guild ID for safety tracking
        """
        if not HAS_TTS or not self.tts:
            self.logger.warning("TTS not available, cannot speak response")
            return
        
        # Set speaking state (prevents STT from hearing our own output)
        self.safety_guard.set_speaking_state(True)
        
        try:
            import tempfile
            
            # Generate TTS audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
            
            self.logger.info(f"Generating TTS for: {text[:50]}...")
            result = await self.tts.speak_to_file(text, tmp_path)
            
            # Verify file was created
            if not result or not os.path.exists(tmp_path):
                self.logger.error(f"TTS file not created: {tmp_path}")
                return
            
            # Wait for file to be fully written
            import time
            max_wait = 5.0
            wait_interval = 0.1
            waited = 0
            
            while waited < max_wait:
                file_size = os.path.getsize(tmp_path)
                if file_size > 0:
                    # Check if file is still growing
                    time.sleep(wait_interval)
                    new_size = os.path.getsize(tmp_path)
                    if new_size == file_size:
                        break  # File is stable
                waited += wait_interval
                time.sleep(wait_interval)
            
            file_size = os.path.getsize(tmp_path)
            self.logger.info(f"TTS file ready: {tmp_path} ({file_size} bytes)")
            
            if file_size == 0:
                self.logger.error("TTS file is empty")
                return
            
            # Play audio
            success = await self._play_audio_file(voice_client, tmp_path)
            
            if success:
                # Record response for loop detection
                if guild_id:
                    self.safety_guard.record_demi_response(guild_id, text)
            
            # Cleanup
            try:
                os.remove(tmp_path)
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"TTS error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            # Clear speaking state
            self.safety_guard.set_speaking_state(False)
    
    async def _process_utterance(self, session: VoiceSession, buffer: AudioBuffer):
        """Process completed utterance through STT.
        
        Args:
            session: Active voice session
            buffer: Audio buffer containing utterance
        """
        # Get buffer contents and clear
        audio_data, user_id = buffer.get_and_clear()
        
        # Skip if buffer too small
        if len(audio_data) < 3200:  # Min 100ms
            return
        
        # Skip if STT not available
        if not HAS_STT or not self.stt:
            return
        
        try:
            # Transcribe audio
            transcription = await self._transcribe_audio(audio_data)
            
            if not transcription or not transcription.text:
                return
            
            text = transcription.text.strip()
            self.logger.info(f"Transcribed: '{text}' from user {user_id}")
            
            # Check for wake word if not already active
            if not session.wake_word_detected:
                if self._check_wake_word(text):
                    self.logger.info(f"Wake word detected from user {user_id}")
                    session.wake_word_detected = True
                    
                    # Play acknowledgment sound
                    await self._play_wake_acknowledgment(session.voice_client)
                    
                    # If only wake word spoken, wait for more
                    if len(text.split()) <= 2:
                        return
                else:
                    # No wake word, ignore (unless always-listening mode)
                    if not self.listen_after_response:
                        return
            
            # Process through Conductor
            await self._process_voice_command(session, user_id, text)
            
            # Reset wake word detection for next interaction
            if not self.listen_after_response:
                session.wake_word_detected = False
                
        except Exception as e:
            self.logger.error(f"Error processing utterance: {e}")
    
    async def _transcribe_audio(self, audio_buffer: bytes) -> Optional["TranscriptionResult"]:
        """Transcribe audio buffer using STT.
        
        Args:
            audio_buffer: PCM audio data
            
        Returns:
            Transcription result or None
        """
        if not HAS_STT or not self.stt:
            return None
        
        try:
            # Create temporary WAV file for STT
            import wave
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                
                # Write WAV file
                with wave.open(tmp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(16000)  # 16kHz
                    wav_file.writeframes(audio_buffer)
            
            # Transcribe using STT
            result = await self.stt.transcribe_file(tmp_path)
            
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            
            return result
            
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return None
    
    async def _process_voice_command(
        self, 
        session: VoiceSession, 
        user_id: int, 
        text: str
    ):
        """Process transcribed voice command through LLM and respond.
        
        Args:
            session: Active voice session
            user_id: Discord user ID
            text: Transcribed text
        """
        self.logger.info(f"Processing voice command: '{text}'")
        
        # Get user info
        user = self.bot.get_user(user_id)
        user_name = str(user) if user else f"User_{user_id}"
        
        # Log user speech
        self.transcript_logger.log_user_speech(
            text=text,
            guild_id=session.guild_id,
            channel_id=session.channel_id,
            user_id=user_id,
            username=user_name,
            session_id=session.session_id
        )
        
        # Mark session as processing
        session.is_speaking = True
        
        try:
            # Build message for Conductor
            messages = [{
                "role": "user", 
                "content": f"[Voice] {user_name}: {text}"
            }]
            
            # Request inference from Conductor
            if self.conductor:
                response = await self.conductor.request_inference(messages)
            else:
                response = "I'm not connected to my brain right now."
            
            # Extract response content
            if isinstance(response, dict):
                response_text = response.get("content", "")
                emotion_state = response.get("emotion_state", {})
            else:
                response_text = response
                emotion_state = {}
            
            self.logger.info(f"LLM response: '{response_text[:50]}...'")
            
            # Log Demi's response
            self.transcript_logger.log_demi_response(
                text=response_text,
                guild_id=session.guild_id,
                channel_id=session.channel_id,
                session_id=session.session_id
            )
            
            # Speak response via TTS
            await self._speak_response(
                session.voice_client, 
                response_text, 
                emotion_state
            )
            
        except Exception as e:
            self.logger.error(f"Voice command processing error: {e}")
            # Play error message
            error_msg = "I'm sorry, I didn't catch that."
            
            # Log error response
            self.transcript_logger.log_demi_response(
                text=error_msg,
                guild_id=session.guild_id,
                channel_id=session.channel_id,
                session_id=session.session_id
            )
            
            await self._speak_response(session.voice_client, error_msg, {})
        
        finally:
            session.is_speaking = False
            session.last_activity = datetime.now()
    
    async def _speak_response(
        self, 
        voice_client: discord.VoiceClient, 
        text: str,
        emotion_state: dict
    ):
        """Synthesize and play TTS audio in voice channel.
        
        Args:
            voice_client: Discord voice client
            text: Text to speak
            emotion_state: Emotional state for voice modulation
        """
        if not voice_client.is_connected():
            return
        
        # Skip if TTS not available
        if not HAS_TTS or not self.tts:
            self.logger.warning("TTS not available, cannot speak response")
            return
        
        # Wait if already playing
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
        
        try:
            # Create emotion object if available
            emotion_obj = None
            if HAS_EMOTIONAL_STATE and emotion_state:
                try:
                    emotion_obj = EmotionalState.from_dict(emotion_state)
                except Exception:
                    pass
            
            # Synthesize speech
            audio_data = await self.tts.synthesize(text, emotion_state=emotion_obj)
            
            if not audio_data:
                self.logger.error("TTS synthesis failed")
                return
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(audio_data)
            
            # Play audio using FFmpeg
            await self._play_audio_file(voice_client, tmp_path)
            
        except Exception as e:
            self.logger.error(f"TTS playback error: {e}")
    
    async def _speak_in_channel(
        self, 
        voice_client: discord.VoiceClient, 
        audio_path: str
    ) -> bool:
        """Play audio file in voice channel.
        
        Args:
            voice_client: Discord voice client
            audio_path: Path to audio file
            
        Returns:
            True if playback started
        """
        if not voice_client.is_connected():
            return False
        
        # Wait if already playing
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
        
        try:
            return await self._play_audio_file(voice_client, audio_path)
        except Exception as e:
            self.logger.error(f"Audio playback error: {e}")
            return False
    
    async def _play_audio_file(
        self, 
        voice_client: discord.VoiceClient, 
        audio_path: str
    ) -> bool:
        """Play audio file using FFmpeg.
        
        Args:
            voice_client: Discord voice client
            audio_path: Path to audio file
            
        Returns:
            True if playback started
            
        Note:
            Requires FFmpeg to be installed on the system.
        """
        try:
            if not os.path.exists(audio_path):
                self.logger.error(f"Audio file not found: {audio_path}")
                return False
            
            # Create audio source using FFmpeg
            audio_source = discord.FFmpegPCMAudio(audio_path)
            
            # Wrap with volume control
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=1.0)
            
            # Play with callback
            voice_client.play(
                audio_source, 
                after=lambda e: self._on_playback_finished(e, audio_path)
            )
            
            self.logger.info(f"Playing audio: {audio_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing audio file: {e}")
            return False
    
    def _on_playback_finished(self, error: Optional[Exception], audio_path: str):
        """Callback when audio playback completes.
        
        Args:
            error: Error if playback failed
            audio_path: Path to audio file
        """
        if error:
            self.logger.error(f"Playback error: {error}")
        
        # Clean up temp file
        try:
            if os.path.exists(audio_path) and audio_path.startswith(tempfile.gettempdir()):
                os.remove(audio_path)
                self.logger.debug(f"Cleaned up temp audio file: {audio_path}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up audio file: {e}")
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if text contains wake word (case-insensitive).
        
        Args:
            text: Transcribed text to check
            
        Returns:
            True if wake word detected
        """
        text_lower = text.lower().strip()
        wake_word_lower = self.wake_word.lower()
        
        # Exact match at start or contained in sentence
        return (
            text_lower.startswith(wake_word_lower) or
            f" {wake_word_lower}" in text_lower or
            f"hey {wake_word_lower}" in text_lower
        )
    
    def _should_timeout(self, session: VoiceSession) -> bool:
        """Check if voice session should timeout due to inactivity.
        
        Args:
            session: Voice session to check
            
        Returns:
            True if session should timeout
        """
        if not self.voice_timeout_sec:
            return False
        
        inactive_duration = (datetime.now() - session.last_activity).total_seconds()
        return inactive_duration > self.voice_timeout_sec
    
    def _opus_to_pcm(self, opus_data: bytes) -> bytes:
        """Convert Discord Opus audio to 16-bit PCM.
        
        Discord sends Opus-encoded audio at 48kHz stereo.
        We need 16kHz mono for Whisper STT.
        
        Args:
            opus_data: Opus-encoded audio packet
            
        Returns:
            16kHz mono PCM audio data
        """
        try:
            # Try to use opuslib for decoding
            try:
                import opuslib
            except ImportError:
                # Fallback: return empty (voice receive won't work without opuslib)
                return b""
            
            # Initialize decoder if needed
            if not self._opus_decoder:
                self._opus_decoder = opuslib.Decoder(48000, 2)  # 48kHz stereo
            
            # Decode Opus to PCM (20ms frame = 960 samples at 48kHz)
            pcm_stereo = self._opus_decoder.decode(opus_data, 960)
            
            # Convert stereo to mono
            pcm_mono = audioop.tomono(pcm_stereo, 2, 0.5, 0.5)
            
            # Resample 48kHz → 16kHz
            pcm_16k, _ = audioop.ratecv(pcm_mono, 2, 1, 48000, 16000, None)
            
            return pcm_16k
            
        except Exception as e:
            self.logger.debug(f"Opus decode error: {e}")
            return b""
    
    def _detect_speech(self, pcm_data: bytes) -> bool:
        """Run VAD on PCM audio.
        
        Args:
            pcm_data: PCM audio data
            
        Returns:
            True if speech detected
        """
        if not HAS_VAD or not self.vad:
            # Fallback: assume speech if we have enough data
            return len(pcm_data) > 1600  # > 50ms at 16kHz
        
        try:
            # VAD expects 30ms frames at 16kHz = 480 samples = 960 bytes (16-bit)
            frame_duration_ms = 30
            frame_size = int(16000 * frame_duration_ms / 1000) * 2
            
            if len(pcm_data) < frame_size:
                return False
            
            # Take last frame
            frame = pcm_data[-frame_size:]
            
            return self.vad.is_speech(frame, 16000)
            
        except Exception as e:
            self.logger.debug(f"VAD error: {e}")
            return False
    
    async def _play_join_sound(self, voice_client: discord.VoiceClient):
        """Play optional join sound when entering channel.
        
        Args:
            voice_client: Discord voice client
        """
        # Optional: play a subtle sound to indicate presence
        # This can be implemented with a pre-recorded sound file
        pass
    
    async def _play_wake_acknowledgment(self, voice_client: discord.VoiceClient):
        """Play acknowledgment sound when wake word detected.
        
        Args:
            voice_client: Discord voice client
        """
        # Optional: play subtle "listening" sound
        # This can be implemented with a pre-recorded sound file
        pass
