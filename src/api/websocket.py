from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Set
import asyncio
import json
from datetime import datetime, timezone

from src.api.auth import verify_token
from src.api.messages import (
    store_message,
    get_conversation_history,
    mark_as_read,
    mark_as_delivered,
)
from src.core.logger import DemiLogger

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = DemiLogger()


class ConnectionManager:
    """Manage active WebSocket connections for real-time messaging"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # user_id -> websocket

    async def connect(self, user_id: str, websocket: WebSocket):
        """Register new connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: user {user_id}")

    def disconnect(self, user_id: str):
        """Remove connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: user {user_id}")

    async def send_message(self, user_id: str, event: str, data: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(
                    {
                        "event": event,
                        "data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast_typing(self, user_id: str, is_typing: bool):
        """Send typing indicator"""
        await self.send_message(user_id, "typing", {"is_typing": is_typing})


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for bidirectional real-time messaging.

    Client sends:
    {
      "event": "message",
      "data": {"content": "Hey Demi"}
    }

    Server sends (Demi's response):
    {
      "event": "message",
      "data": {
        "message_id": "uuid",
        "sender": "demi",
        "content": "Yeah?",
        "emotion_state": {...},
        "created_at": "..."
      },
      "timestamp": "..."
    }

    Server also sends:
    - typing events: {"event": "typing", "data": {"is_typing": true}}
    - read_receipt events: {"event": "read_receipt", "data": {"message_id": "..."}}
    - delivered events: {"event": "delivered", "data": {"message_id": "..."}}
    """

    # Verify JWT token
    try:
        payload = verify_token(token, token_type="access")
        user_id = payload["user_id"]
        conversation_id = user_id  # For v1, conversation_id = user_id (1-1 chat)
    except HTTPException as e:
        await websocket.close(code=1008, reason=str(e.detail))
        return

    # Connect
    await manager.connect(user_id, websocket)

    try:
        # Send conversation history (last 7 days)
        history = await get_conversation_history(conversation_id, days=7, limit=100)
        await websocket.send_json(
            {
                "event": "history",
                "data": {
                    "messages": [msg.to_dict() for msg in history],
                    "count": len(history),
                },
            }
        )

        # Main message loop
        while True:
            # Receive message from Android client
            raw_data = await websocket.receive_json()
            event = raw_data.get("event")
            data = raw_data.get("data", {})

            if event == "message":
                # Store user's message
                user_content = data.get("content", "").strip()
                if not user_content:
                    continue

                user_message = await store_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    sender="user",
                    content=user_content,
                )

                # Mark as delivered immediately
                await mark_as_delivered(user_message.message_id)

                # Send typing indicator
                await manager.broadcast_typing(user_id, is_typing=True)

                # Get Demi's response via Conductor
                try:
                    # Import conductor (avoid circular import)
                    from src.conductor.orchestrator import get_conductor_instance

                    conductor = get_conductor_instance()

                    response = await conductor.request_inference_for_platform(
                        platform="android",
                        user_id=user_id,
                        content=user_content,
                        context={
                            "source": "android_websocket",
                            "conversation_id": conversation_id,
                            "message_id": user_message.message_id,
                        },
                    )

                    # Stop typing indicator
                    await manager.broadcast_typing(user_id, is_typing=False)

                    # Store Demi's response
                    emotion_state = response.get("emotion_state", {})
                    demi_message = await store_message(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        sender="demi",
                        content=response.get("content", ""),
                        emotion_state=emotion_state,
                    )

                    # Send response to client
                    await websocket.send_json(
                        {
                            "event": "message",
                            "data": demi_message.to_dict(),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                except Exception as e:
                    logger.error(f"LLM inference error: {e}")
                    await manager.broadcast_typing(user_id, is_typing=False)
                    await websocket.send_json(
                        {
                            "event": "error",
                            "data": {"message": "Error generating response"},
                        }
                    )

            elif event == "read_receipt":
                # Mark message as read
                message_id = data.get("message_id")
                if message_id:
                    await mark_as_read(message_id)

            elif event == "ping":
                # Keepalive
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)


# Export manager for autonomous messages (Plan 03)
def get_connection_manager() -> ConnectionManager:
    """Get singleton connection manager"""
    return manager
