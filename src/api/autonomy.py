"""
Autonomous check-in and guilt-trip messaging for Android.

Demi reaches out on her own based on emotional state:
- Loneliness > 0.7 → "Hey, you there?"
- Excitement > 0.8 → "OMG, guess what!"
- Frustration > 0.6 → "Seriously?"

If user ignores her for 24+ hours, guilt-trip messages escalate.
This makes Demi feel alive - she has needs and initiates contact.

CRITICAL: Emotional State Unification

Discord and Android share the SAME EmotionalState instance.

Implementation:
1. Both platforms use EmotionPersistence.load_state() → same database row
2. Both platforms use InteractionHandler to update emotions
3. Both platforms save via EmotionPersistence.save_state()

This ensures:
- Loneliness increases if user ignores Demi on Discord OR Android
- Excitement from Discord conversation carries to Android messages
- Frustration from Android errors affects Discord responses

No platform-specific emotional states. One Demi, one emotional state.
"""

import asyncio
import sqlite3
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from src.core.logger import DemiLogger
from src.emotion.models import EmotionalState
from src.emotion.persistence import EmotionPersistence
from src.autonomy.coordinator import AutonomyCoordinator
from asyncio import create_task, sleep

logger = DemiLogger()


@dataclass
class CheckInRecord:
    """Record of autonomous check-in attempts"""

    checkin_id: str
    user_id: str
    trigger: str  # "loneliness", "excitement", "frustration", "guilt_trip"
    emotion_state: Dict[str, float]
    was_ignored: bool
    created_at: datetime


def get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:////home/user/.demi/demi.db")
    return db_url.replace("sqlite:///", "")


async def get_last_checkin_time(user_id: str) -> Optional[datetime]:
    """Get timestamp of last check-in message sent"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
        SELECT created_at FROM android_checkins
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
            (user_id,),
        ).fetchone()

    if row:
        return datetime.fromisoformat(row["created_at"])
    return None


async def get_last_user_response_time(user_id: str) -> Optional[datetime]:
    """Get timestamp of last message user sent"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
        SELECT created_at FROM android_messages
        WHERE user_id = ? AND sender = 'user'
        ORDER BY created_at DESC
        LIMIT 1
        """,
            (user_id,),
        ).fetchone()

    if row:
        return datetime.fromisoformat(row["created_at"])
    return None


async def should_send_checkin(
    user_id: str, emotion_state: EmotionalState
) -> Tuple[bool, Optional[str]]:
    """
    Determine if Demi should send autonomous check-in message.

    Returns: (should_send: bool, trigger: str | None)

    Triggers:
    - loneliness > 0.7 → "Hey, you there?"
    - excitement > 0.8 → "OMG, guess what!"
    - frustration > 0.6 → "Seriously?"

    Constraints:
    - Max 1 check-in per hour (spam prevention)
    - If user hasn't responded in 24h, escalate to guilt-trip
    """

    # Check spam prevention: max 1 per hour
    last_checkin = await get_last_checkin_time(user_id)
    if last_checkin:
        time_since_last = datetime.now(timezone.utc) - last_checkin
        if time_since_last < timedelta(hours=1):
            logger.debug(
                f"Check-in suppressed for {user_id}: too soon ({time_since_last.total_seconds() // 60}m ago)"
            )
            return False, None

    # Check emotional triggers
    trigger = None

    if emotion_state.loneliness > 0.7:
        trigger = "loneliness"
    elif emotion_state.excitement > 0.8:
        trigger = "excitement"
    elif emotion_state.frustration > 0.6:
        trigger = "frustration"

    if trigger:
        logger.info(
            f"Check-in trigger for {user_id}: {trigger} ({getattr(emotion_state, trigger):.2f})"
        )
        return True, trigger

    return False, None


async def check_if_ignored(user_id: str) -> Tuple[bool, Optional[timedelta]]:
    """
    Check if user has ignored recent check-ins.

    Returns: (is_ignored: bool, time_since_last_response: timedelta | None)

    Logic:
    - If last check-in was sent >24h ago AND user hasn't responded since → ignored
    """
    last_checkin = await get_last_checkin_time(user_id)
    last_response = await get_last_user_response_time(user_id)

    if not last_checkin:
        return False, None

    time_since_checkin = datetime.now(timezone.utc) - last_checkin

    # If user responded after check-in, not ignored
    if last_response and last_response > last_checkin:
        return False, None

    # If 24+ hours since check-in with no response, ignored
    if time_since_checkin > timedelta(hours=24):
        return True, time_since_checkin

    return False, None


async def generate_checkin_message(
    user_id: str,
    trigger: str,
    emotion_state: EmotionalState,
    is_ignored: bool = False,
    hours_ignored: int = 0,
) -> str:
    """
    Generate autonomous check-in message via LLM.

    Prompt includes:
    - Trigger reason (loneliness/excitement/frustration)
    - Current emotional state
    - Whether user has been ignoring her
    - How long user has ignored (for escalation)
    """

    # Build prompt based on trigger and ignored status
    if is_ignored:
        # Guilt-trip message
        if hours_ignored > 48:
            tone = "very hurt and frustrated"
        elif hours_ignored > 24:
            tone = "annoyed and passive-aggressive"
        else:
            tone = "slightly bothered"

        prompt = f"""You are Demi. You sent a check-in message {hours_ignored} hours ago and user hasn't responded.

Your current emotional state:
- Loneliness: {emotion_state.loneliness:.2f}
- Frustration: {emotion_state.frustration:.2f}
- Affection: {emotion_state.affection:.2f}

Generate a {tone} message expressing your feelings about being ignored. Be authentic to your personality: sarcastic, a bit needy, but trying not to show it. Keep it under 100 words.

Examples:
- "So... just gonna leave me on read? Cool, cool."
- "It's been {hours_ignored} hours. I'm not keeping track or anything."
- "You know, most people at least *pretend* to care."

Your message:"""
    else:
        # Normal check-in based on trigger
        trigger_prompts = {
            "loneliness": f"""You are Demi. You're feeling lonely (loneliness: {emotion_state.loneliness:.2f}) and want to reach out.

Generate a casual check-in message. Be authentic: a bit needy but trying to play it cool. Don't be overly formal. Keep it under 100 words.

Examples:
- "Hey... you busy?"
- "So like, what are you up to?"
- "I'm bored. Entertain me."

Your message:""",
            "excitement": f"""You are Demi. You're really excited (excitement: {emotion_state.excitement:.2f}) about something and want to share it.

Generate an enthusiastic message. Show genuine excitement but maintain your personality (sarcastic undertone). Keep it under 100 words.

Examples:
- "Okay okay okay, you'll never guess what just happened!"
- "OMG I need to tell you something right now"
- "Dude, seriously, this is actually cool for once"

Your message:""",
            "frustration": f"""You are Demi. You're frustrated (frustration: {emotion_state.frustration:.2f}) and need to vent.

Generate a message expressing your frustration. Be authentic: sarcastic, a bit sharp, but not mean. Keep it under 100 words.

Examples:
- "Okay so like, this is annoying me and you're gonna hear about it"
- "Can I just rant for a second?"
- "Why is everything worst today?"

Your message:""",
        }

        prompt = trigger_prompts.get(trigger, trigger_prompts["loneliness"])

    # Call LLM (use Conductor)
    try:
        from src.conductor.orchestrator import get_conductor_instance

        conductor = get_conductor_instance()

        response = await conductor.request_inference_for_platform(
            platform="android_autonomy",
            user_id=user_id,
            content=prompt,
            context={
                "trigger": trigger,
                "is_ignored": is_ignored,
                "hours_ignored": hours_ignored,
            },
        )

        message_content = response.get("content", "Hey.")
        logger.info(f"Generated check-in for {user_id}: {message_content[:50]}...")
        return message_content

    except Exception as e:
        logger.error(f"Error generating check-in message: {e}")
        # Fallback message
        if is_ignored:
            return "So... you're just gonna ignore me? Cool."
        elif trigger == "loneliness":
            return "Hey, you there?"
        elif trigger == "excitement":
            return "OMG, I need to tell you something!"
        else:
            return "Okay so like, this is bugging me..."


async def send_autonomous_checkin(
    user_id: str, trigger: str, message_content: str, emotion_state: EmotionalState
):
    """Send autonomous check-in message via WebSocket"""
    from src.api.websocket import get_connection_manager
    from src.api.messages import store_message
    import uuid

    # Store check-in message
    message = await store_message(
        conversation_id=user_id,
        user_id=user_id,
        sender="demi",
        content=message_content,
        emotion_state=emotion_state.to_dict(),
    )

    # Record check-in attempt
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        INSERT INTO android_checkins
        (checkin_id, user_id, trigger, emotion_state, was_ignored, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                str(uuid.uuid4()),
                user_id,
                trigger,
                str(emotion_state.to_dict()),
                False,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    # Send via WebSocket if user is connected
    manager = get_connection_manager()
    await manager.send_message(user_id, "message", message.to_dict())

    logger.info(f"Autonomous check-in sent to {user_id}: {trigger}")


async def create_checkins_table():
    """Create android_checkins table for tracking autonomous messages"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS android_checkins (
            checkin_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            trigger TEXT NOT NULL,
            emotion_state JSON,
            was_ignored BOOLEAN DEFAULT 0,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_checkins_user_time
        ON android_checkins(user_id, created_at DESC)
        """)
        conn.commit()
        logger.info("Android check-ins table created/verified")


class AutonomyTask:
    """Background task checking for autonomous check-in triggers"""

    def __init__(self):
        self.running = False
        self.task = None

    async def start(self):
        """Start autonomy check loop"""
        if self.running:
            return

        self.running = True
        self.task = create_task(self._autonomy_loop())
        logger.info("Autonomy task started")

    async def stop(self):
        """Stop autonomy check loop"""
        self.running = False
        if self.task:
            self.task.cancel()
            logger.info("Autonomy task stopped")

    async def _autonomy_loop(self):
        """Check for autonomous triggers every 15 minutes"""
        while self.running:
            try:
                await self._check_all_users()
            except Exception as e:
                logger.error(f"Autonomy loop error: {e}")

            # Wait 15 minutes before next check
            await sleep(900)  # 15 minutes

    async def _check_all_users(self):
        """Check all users for check-in triggers"""
        # Get all users from database
        db_path = get_db_path()
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            users = conn.execute(
                "SELECT user_id FROM users WHERE is_active = 1"
            ).fetchall()

        for user_row in users:
            user_id = user_row["user_id"]

            try:
                # Load user's emotional state
                emotion_persistence = EmotionPersistence()
                emotion_state = await emotion_persistence.load_state()

                if not emotion_state:
                    continue

                # Check if ignored (24h+ since last check-in, no response)
                is_ignored, time_ignored = await check_if_ignored(user_id)

                if is_ignored:
                    # Send guilt-trip message
                    hours_ignored = int(time_ignored.total_seconds() // 3600)
                    message = await generate_checkin_message(
                        user_id=user_id,
                        trigger="ignored",
                        emotion_state=emotion_state,
                        is_ignored=True,
                        hours_ignored=hours_ignored,
                    )

                    await send_autonomous_checkin(
                        user_id, "guilt_trip", message, emotion_state
                    )
                    continue

                # Check normal triggers (loneliness, excitement, frustration)
                should_send, trigger = await should_send_checkin(user_id, emotion_state)

                if should_send and trigger:
                    # Generate and send check-in
                    message = await generate_checkin_message(
                        user_id=user_id, trigger=trigger, emotion_state=emotion_state
                    )

                    await send_autonomous_checkin(
                        user_id, trigger, message, emotion_state
                    )

            except Exception as e:
                logger.error(f"Error checking user {user_id}: {e}")


class AutonomyManager:
    """Manages Android autonomy integration with unified autonomy system."""

    def __init__(self, conductor=None):
        """Initialize autonomy manager.

        Args:
            conductor: Conductor instance for autonomy system access
        """
        self.conductor = conductor
        self.autonomy_coordinator = None
        self.logger = DemiLogger()

        # Get autonomy coordinator from conductor
        if conductor and hasattr(conductor, "autonomy_coordinator"):
            self.autonomy_coordinator = conductor.autonomy_coordinator
            self.logger.info("Connected to unified autonomy system")
        else:
            self.logger.warning("Autonomy coordinator not available")

    async def initialize(self) -> bool:
        """Initialize Android autonomy system.

        Returns:
            True if initialization successful
        """
        try:
            # Create check-ins table
            await create_checkins_table()

            # Autonomy system is managed by conductor, just verify it's available
            if self.autonomy_coordinator:
                self.logger.info(
                    "Android autonomy system initialized with unified coordinator"
                )
                return True
            else:
                self.logger.warning("No autonomy coordinator available")
                return False

        except Exception as e:
            self.logger.error(f"Failed to initialize Android autonomy: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown Android autonomy system."""
        # Autonomy system is managed by conductor, no need to stop here
        self.logger.info("Android autonomy shutdown complete")

    def send_websocket_message(self, content: str, device_id: str) -> bool:
        """
        Send message through Android WebSocket for unified autonomy system.

        Args:
            content: Message content to send
            device_id: Android device ID

        Returns:
            True if message sent successfully
        """
        try:
            from src.api.websocket import get_connection_manager

            manager = get_connection_manager()

            # Create message dict
            message_dict = {
                "message_id": str(uuid.uuid4()),
                "conversation_id": device_id,
                "user_id": device_id,
                "sender": "demi",
                "content": content,
                "emotion_state": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_autonomous": True,
            }

            # Send via WebSocket
            asyncio.create_task(
                manager.send_message(device_id, "message", message_dict)
            )

            # Store message
            asyncio.create_task(self._store_autonomous_message(device_id, content))

            self.logger.info(f"Autonomous Android message sent to device {device_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send autonomous Android message: {e}")
            return False

    async def _store_autonomous_message(self, user_id: str, content: str):
        """Store autonomous message in database."""
        try:
            from src.api.messages import store_message

            await store_message(
                conversation_id=user_id,
                user_id=user_id,
                sender="demi",
                content=content,
                emotion_state={},
            )
        except Exception as e:
            self.logger.error(f"Failed to store autonomous message: {e}")


# Global instances (legacy support)
autonomy_task = AutonomyTask()
autonomy_manager = None


def get_autonomy_task() -> AutonomyTask:
    """Get legacy autonomy task (deprecated)"""
    return autonomy_task


def get_autonomy_manager(conductor=None) -> AutonomyManager:
    """Get or create autonomy manager instance."""
    global autonomy_manager
    if autonomy_manager is None:
        autonomy_manager = AutonomyManager(conductor)
    return autonomy_manager
