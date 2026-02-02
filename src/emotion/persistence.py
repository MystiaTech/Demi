# src/emotion/persistence.py
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from pathlib import Path
from src.emotion.models import EmotionalState
from src.emotion.decay import DecaySystem
from src.emotion.interactions import InteractionType


class EmotionPersistence:
    """
    Handles persistent storage and recovery of emotional state.
    Integrates with DecaySystem to simulate offline emotion progression.
    """

    def __init__(self, db_path: str = "~/.demi/emotions.db"):
        """
        Initialize persistence layer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema if needed
        self._init_schema()

    def _init_schema(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main emotional state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emotional_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                
                -- 9 emotions
                loneliness REAL NOT NULL,
                excitement REAL NOT NULL,
                frustration REAL NOT NULL,
                jealousy REAL NOT NULL,
                vulnerability REAL NOT NULL,
                confidence REAL NOT NULL,
                curiosity REAL NOT NULL,
                affection REAL NOT NULL,
                defensiveness REAL NOT NULL,
                
                -- Momentum tracking
                momentum_json TEXT NOT NULL,
                
                -- Metadata
                notes TEXT,
                
                UNIQUE(timestamp)
            )
        """)

        # Interaction log (audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interaction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                interaction_type TEXT NOT NULL,
                user_message TEXT,
                
                -- State before interaction
                state_before_json TEXT NOT NULL,
                
                -- State after interaction
                state_after_json TEXT NOT NULL,
                
                -- Effect details
                effects_json TEXT NOT NULL,
                
                -- Metadata
                confidence_level REAL,  -- 0-1 how sure about effect
                notes TEXT
            )
        """)

        # Create indexes for interaction log
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interaction_timestamp 
            ON interaction_log(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interaction_type 
            ON interaction_log(interaction_type)
        """)

        # Backup snapshots (hourly)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL UNIQUE,
                state_json TEXT NOT NULL,
                snapshot_type TEXT DEFAULT 'hourly'  -- hourly, manual, startup, shutdown
            )
        """)

        conn.commit()
        conn.close()

    def save_state(self, state: EmotionalState, notes: Optional[str] = None) -> bool:
        """
        Save current emotional state to database.

        Args:
            state: EmotionalState to persist
            notes: Optional notes about what triggered this state

        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc)

            cursor.execute(
                """
                INSERT INTO emotional_state 
                (timestamp, loneliness, excitement, frustration, jealousy, vulnerability,
                 confidence, curiosity, affection, defensiveness, momentum_json, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    now.isoformat(),
                    state.loneliness,
                    state.excitement,
                    state.frustration,
                    state.jealousy,
                    state.vulnerability,
                    state.confidence,
                    state.curiosity,
                    state.affection,
                    state.defensiveness,
                    json.dumps(state.momentum),
                    notes,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Failed to save emotional state: {e}")
            return False

    def load_latest_state(self) -> Optional[EmotionalState]:
        """
        Load the most recent saved emotional state.

        Returns:
            EmotionalState or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT loneliness, excitement, frustration, jealousy, vulnerability,
                       confidence, curiosity, affection, defensiveness, momentum_json, timestamp
                FROM emotional_state
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            state = EmotionalState(
                loneliness=row[0],
                excitement=row[1],
                frustration=row[2],
                jealousy=row[3],
                vulnerability=row[4],
                confidence=row[5],
                curiosity=row[6],
                affection=row[7],
                defensiveness=row[8],
            )
            state.momentum = json.loads(row[9])

            return state
        except Exception as e:
            print(f"Failed to load emotional state: {e}")
            return None

    def restore_and_age_state(
        self, decay_system: DecaySystem
    ) -> Optional[EmotionalState]:
        """
        Restore emotional state from database and simulate offline decay.

        This is the main restore function called on startup:
        1. Load last saved state
        2. Calculate how long we were offline
        3. Simulate emotion decay for that period
        4. Return aged state

        Args:
            decay_system: DecaySystem instance for offline simulation

        Returns:
            Aged emotional state, or None if no saved state
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT loneliness, excitement, frustration, jealousy, vulnerability,
                       confidence, curiosity, affection, defensiveness, momentum_json, timestamp
                FROM emotional_state
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Reconstruct state
            state = EmotionalState(
                loneliness=row[0],
                excitement=row[1],
                frustration=row[2],
                jealousy=row[3],
                vulnerability=row[4],
                confidence=row[5],
                curiosity=row[6],
                affection=row[7],
                defensiveness=row[8],
            )
            state.momentum = json.loads(row[9])
            last_save_time = datetime.fromisoformat(row[10])

            # Calculate offline duration
            now = datetime.now(timezone.utc)
            offline_seconds = int((now - last_save_time).total_seconds())

            # Simulate decay for offline period
            aged_state = decay_system.simulate_offline_decay(state, offline_seconds)

            return aged_state
        except Exception as e:
            print(f"Failed to restore and age state: {e}")
            # Return None to start fresh
            return None

    def log_interaction(
        self,
        interaction_type: InteractionType,
        state_before: EmotionalState,
        state_after: EmotionalState,
        effects: Dict,
        user_message: Optional[str] = None,
        confidence_level: float = 1.0,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Log an interaction with before/after emotional states.

        Args:
            interaction_type: What happened
            state_before: Emotional state before interaction
            state_after: Emotional state after interaction
            effects: Effect dictionary from InteractionHandler
            user_message: The user's message (if applicable)
            confidence_level: How confident we are about the effect (0-1)
            notes: Optional notes

        Returns:
            True if logged successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc)

            cursor.execute(
                """
                INSERT INTO interaction_log
                (timestamp, interaction_type, user_message, state_before_json, 
                 state_after_json, effects_json, confidence_level, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    now.isoformat(),
                    interaction_type.value,
                    user_message,
                    json.dumps(state_before.to_dict()),
                    json.dumps(state_after.to_dict()),
                    json.dumps(effects),
                    confidence_level,
                    notes,
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Failed to log interaction: {e}")
            return False

    def get_interaction_history(
        self, limit: int = 100, interaction_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve recent interaction history.

        Args:
            limit: Maximum number of records to return
            interaction_type: Filter by type (optional)

        Returns:
            List of interaction dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if interaction_type:
                cursor.execute(
                    """
                    SELECT timestamp, interaction_type, user_message, state_before_json,
                           state_after_json, effects_json, confidence_level, notes
                    FROM interaction_log
                    WHERE interaction_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (interaction_type, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT timestamp, interaction_type, user_message, state_before_json,
                           state_after_json, effects_json, confidence_level, notes
                    FROM interaction_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "timestamp": row[0],
                    "interaction_type": row[1],
                    "user_message": row[2],
                    "state_before": json.loads(row[3]),
                    "state_after": json.loads(row[4]),
                    "effects": json.loads(row[5]),
                    "confidence_level": row[6],
                    "notes": row[7],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Failed to retrieve interaction history: {e}")
            return []

    def create_backup_snapshot(
        self, state: EmotionalState, snapshot_type: str = "manual"
    ):
        """
        Create a backup snapshot of the current state.
        Called hourly automatically or on manual request.

        Args:
            state: State to snapshot
            snapshot_type: one of 'hourly', 'manual', 'startup', 'shutdown'
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc)

            cursor.execute(
                """
                INSERT INTO state_snapshots (timestamp, state_json, snapshot_type)
                VALUES (?, ?, ?)
            """,
                (
                    now.isoformat(),
                    json.dumps(state.to_dict()),
                    snapshot_type,
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to create backup snapshot: {e}")

    def restore_from_backup(
        self, backup_age_hours: int = 1
    ) -> Optional[EmotionalState]:
        """
        Restore state from a recent backup snapshot.
        Used if primary state is corrupted.

        Args:
            backup_age_hours: How far back to look (default 1 hour)

        Returns:
            EmotionalState from backup, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=backup_age_hours)

            cursor.execute(
                """
                SELECT state_json FROM state_snapshots
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 1
            """,
                (cutoff_time.isoformat(),),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            state_dict = json.loads(row[0])
            return EmotionalState.from_dict(state_dict)
        except Exception as e:
            print(f"Failed to restore from backup: {e}")
            return None
