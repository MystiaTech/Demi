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
        
        self.logger.info(
            "DiscordVoiceClient initialized",
            wake_word=self.wake_word,
            timeout_sec=self.voice_timeout_sec,
            stt_available=HAS_STT,
            tts_available=HAS_TTS,
            vad_available=HAS_VAD,
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
            
        except Exception as e:
            self.logger.error(f"Failed to join voice channel: {e}")
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
        self.logger.info(f"Connected to voice channel: {voice_client.channel.name}")
        
        # Play join sound (optional)
        await self._play_join_sound(voice_client)
        
        # Start listening loop
        guild_id = voice_client.guild.id
        task = asyncio.create_task(self._voice_listen_loop(voice_client))
        self._listen_tasks[guild_id] = task
    
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
