import sqlite3
import json
import uuid
import os
from datetime import datetime, timedelta, UTC
from typing import List, Optional, Dict
from src.api.models import AndroidMessage
from src.core.logger import DemiLogger

logger = DemiLogger()


def get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:////home/user/.demi/demi.db")
    return db_url.replace("sqlite:///", "")


async def store_message(
    conversation_id: str,
    user_id: str,
    sender: str,
    content: str,
    emotion_state: Optional[Dict[str, float]] = None,
) -> AndroidMessage:
    """Store message in database"""
    message = AndroidMessage(
        message_id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        user_id=user_id,
        sender=sender,
        content=content,
        emotion_state=emotion_state,
        status="sent",
        created_at=datetime.now(UTC),
    )

    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        INSERT INTO android_messages
        (message_id, conversation_id, user_id, sender, content, emotion_state, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                message.message_id,
                message.conversation_id,
                message.user_id,
                message.sender,
                message.content,
                json.dumps(emotion_state) if emotion_state else None,
                message.status,
                message.created_at.isoformat(),
            ),
        )
        conn.commit()

    logger.info(f"Message stored: {message.message_id} ({sender})")
    return message


async def get_conversation_history(
    conversation_id: str, days: int = 7, limit: int = 100
) -> List[AndroidMessage]:
    """Load last N days of conversation history"""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    db_path = get_db_path()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
        SELECT * FROM android_messages
        WHERE conversation_id = ? AND created_at > ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
            (conversation_id, cutoff.isoformat(), limit),
        ).fetchall()

    messages = []
    for row in reversed(rows):  # Reverse for chronological order
        emotion_state = (
            json.loads(row["emotion_state"]) if row["emotion_state"] else None
        )
        messages.append(
            AndroidMessage(
                message_id=row["message_id"],
                conversation_id=row["conversation_id"],
                user_id=row["user_id"],
                sender=row["sender"],
                content=row["content"],
                emotion_state=emotion_state,
                status=row["status"],
                delivered_at=datetime.fromisoformat(row["delivered_at"])
                if row["delivered_at"]
                else None,
                read_at=datetime.fromisoformat(row["read_at"])
                if row["read_at"]
                else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        )

    return messages


async def mark_as_read(message_id: str) -> None:
    """Mark message as read with timestamp"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        UPDATE android_messages
        SET status = 'read', read_at = ?
        WHERE message_id = ?
        """,
            (datetime.now(UTC).isoformat(), message_id),
        )
        conn.commit()
    logger.debug(f"Message marked read: {message_id}")


async def mark_as_delivered(message_id: str) -> None:
    """Mark message as delivered"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        UPDATE android_messages
        SET status = 'delivered', delivered_at = ?
        WHERE message_id = ? AND status = 'sent'
        """,
            (datetime.now(UTC).isoformat(), message_id),
        )
        conn.commit()
