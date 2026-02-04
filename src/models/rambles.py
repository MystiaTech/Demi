"""Ramble model and database persistence for autonomous message posting.

Rambles are spontaneous messages Demi posts to Discord based on emotional triggers.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Dict, Optional
import json
import sqlite3
import uuid


@dataclass
class Ramble:
    """Spontaneous message posted by Demi"""
    ramble_id: str  # UUID
    channel_id: str
    content: str
    emotion_state: Dict[str, float]  # Emotional state when ramble generated
    trigger: str  # Enum: "loneliness", "excitement", "frustration", "spontaneous"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serialize ramble to dict for database storage."""
        data = asdict(self)
        data["emotion_state"] = json.dumps(data["emotion_state"])
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Ramble":
        """Deserialize ramble from dict (from database)."""
        data = data.copy()
        if isinstance(data["emotion_state"], str):
            data["emotion_state"] = json.loads(data["emotion_state"])
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class RambleStore:
    """Persistence layer for rambles"""

    def __init__(self, db_path: str):
        """Initialize ramble store with database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.ensure_table()

    def ensure_table(self):
        """Create rambles table if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS discord_rambles (
                ramble_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                content TEXT NOT NULL,
                emotion_state JSON NOT NULL,
                trigger TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """)
            conn.commit()

    async def save(self, ramble: Ramble) -> None:
        """Save ramble to database

        Args:
            ramble: Ramble instance to persist
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
            INSERT INTO discord_rambles
            (ramble_id, channel_id, content, emotion_state, trigger, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ramble.ramble_id,
                ramble.channel_id,
                ramble.content,
                json.dumps(ramble.emotion_state),
                ramble.trigger,
                ramble.created_at.isoformat()
            ))
            conn.commit()

    async def get_recent_rambles(self, hours: int = 24) -> list:
        """Get rambles from last N hours

        Args:
            hours: Number of hours to look back

        Returns:
            List of Ramble objects, ordered newest first
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
            SELECT ramble_id, channel_id, content, emotion_state, trigger, created_at
            FROM discord_rambles
            WHERE created_at > datetime('now', ? || ' hours')
            ORDER BY created_at DESC
            """, (f"-{hours}",)).fetchall()

        # Convert rows to Ramble objects (column order matters)
        rambles = []
        for row in rows:
            rambles.append(Ramble(
                ramble_id=row[0],
                channel_id=row[1],
                content=row[2],
                emotion_state=json.loads(row[3]),
                trigger=row[4],
                created_at=datetime.fromisoformat(row[5])
            ))
        return rambles
