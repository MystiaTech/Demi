"""Voice Transcript Logger - Logs all voice channel conversations.

Logs:
- What users say (STT transcripts)
- What Demi says (TTS responses)
- Timestamps and speaker identification
- Guild/channel context
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from src.core.logger import get_logger

logger = get_logger()


@dataclass
class VoiceTranscriptEntry:
    """Single voice transcript entry."""
    timestamp: str
    guild_id: int
    channel_id: int
    user_id: Optional[int]
    username: str
    speaker_type: str  # "user" or "demi"
    text: str
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VoiceTranscriptLogger:
    """Logger for voice channel conversations.
    
    Logs both user speech (via STT) and Demi's responses (TTS).
    Creates daily log files for easy organization.
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """Initialize transcript logger.
        
        Args:
            log_dir: Directory to store transcript logs. Defaults to ~/.demi/voice_logs
        """
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / ".demi" / "voice_logs"
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_file: Optional[Path] = None
        self._entries: list = []
        
        logger.info(f"VoiceTranscriptLogger initialized: {self.log_dir}")
    
    def _get_log_file(self) -> Path:
        """Get log file for current date."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"voice_transcript_{date_str}.jsonl"
    
    def log_user_speech(
        self,
        text: str,
        guild_id: int,
        channel_id: int,
        user_id: int,
        username: str,
        session_id: Optional[str] = None
    ):
        """Log user speech transcript.
        
        Args:
            text: Transcribed text
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            user_id: Discord user ID
            username: Discord username
            session_id: Voice session identifier
        """
        entry = VoiceTranscriptEntry(
            timestamp=datetime.now().isoformat(),
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            username=username,
            speaker_type="user",
            text=text,
            session_id=session_id
        )
        self._write_entry(entry)
        logger.debug(f"[VOICE LOG] User {username}: {text[:50]}...")
    
    def log_demi_response(
        self,
        text: str,
        guild_id: int,
        channel_id: int,
        session_id: Optional[str] = None
    ):
        """Log Demi's response.
        
        Args:
            text: Response text that was spoken
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            session_id: Voice session identifier
        """
        entry = VoiceTranscriptEntry(
            timestamp=datetime.now().isoformat(),
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=None,
            username="Demi",
            speaker_type="demi",
            text=text,
            session_id=session_id
        )
        self._write_entry(entry)
        logger.info(f"[VOICE LOG] Demi: {text[:50]}...")
    
    def _write_entry(self, entry: VoiceTranscriptEntry):
        """Write entry to log file."""
        log_file = self._get_log_file()
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write voice transcript: {e}")
    
    def get_recent_transcripts(
        self,
        guild_id: Optional[int] = None,
        limit: int = 100,
        speaker_type: Optional[str] = None
    ) -> list:
        """Get recent transcript entries.
        
        Args:
            guild_id: Filter by guild
            limit: Maximum entries to return
            speaker_type: Filter by "user" or "demi"
            
        Returns:
            List of VoiceTranscriptEntry dicts
        """
        entries = []
        log_file = self._get_log_file()
        
        if not log_file.exists():
            return entries
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if guild_id and entry.get("guild_id") != guild_id:
                            continue
                        if speaker_type and entry.get("speaker_type") != speaker_type:
                            continue
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read voice transcripts: {e}")
        
        return entries[-limit:]
    
    def get_session_context(
        self,
        session_id: str,
        context_turns: int = 10
    ) -> str:
        """Get conversation context for a session.
        
        Args:
            session_id: Voice session ID
            context_turns: Number of turns to include
            
        Returns:
            Formatted conversation context string
        """
        entries = []
        log_file = self._get_log_file()
        
        if not log_file.exists():
            return ""
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("session_id") == session_id:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to read session context: {e}")
            return ""
        
        # Format as conversation
        lines = []
        for entry in entries[-context_turns * 2:]:  # *2 for user+demi pairs
            speaker = entry.get("username", "Unknown")
            text = entry.get("text", "")
            lines.append(f"{speaker}: {text}")
        
        return "\n".join(lines)


# Global instance
_voice_logger: Optional[VoiceTranscriptLogger] = None


def get_voice_logger() -> VoiceTranscriptLogger:
    """Get global voice transcript logger instance."""
    global _voice_logger
    if _voice_logger is None:
        _voice_logger = VoiceTranscriptLogger()
    return _voice_logger
