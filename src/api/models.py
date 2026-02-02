from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr
import uuid


# Database models
@dataclass
class User:
    """User account (existing account only - no in-app registration)"""

    user_id: str  # UUID
    email: str
    username: str
    password_hash: str  # bcrypt hash
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_login: Optional[datetime] = None
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "locked_until": self.locked_until.isoformat()
            if self.locked_until
            else None,
        }


@dataclass
class Session:
    """Active session for multi-device support"""

    session_id: str  # UUID
    user_id: str  # FK to User
    device_name: str  # "Pixel 7", "Galaxy Tab", etc.
    device_fingerprint: str  # Unique device ID
    refresh_token_hash: str  # bcrypt hash of refresh token
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "device_name": self.device_name,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_active": self.is_active,
        }


# Pydantic request/response schemas
class LoginRequest(BaseModel):
    """User login request (existing account only)"""

    email: EmailStr
    password: str
    device_name: str = "Android Device"
    device_fingerprint: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "MyPassword123!",
                "device_name": "Pixel 7",
                "device_fingerprint": "android-uuid-1234",
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh access token"""

    refresh_token: str

    class Config:
        json_schema_extra = {"example": {"refresh_token": "eyJhbGc..."}}


class TokenResponse(BaseModel):
    """Authentication response with access + refresh tokens"""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int  # seconds (access token)
    refresh_expires_in: int  # seconds (refresh token)
    user_id: str
    email: str
    session_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGc...",
                "refresh_token": "eyJhbGc...",
                "token_type": "bearer",
                "expires_in": 1800,
                "refresh_expires_in": 604800,
                "user_id": "uuid-1234",
                "email": "user@example.com",
                "session_id": "session-uuid-5678",
            }
        }


class SessionResponse(BaseModel):
    """Active session details"""

    session_id: str
    device_name: str
    created_at: str
    last_activity: str
    expires_at: str
    is_active: bool
    is_current: bool  # True if this is the session making the request

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-1234",
                "device_name": "Pixel 7",
                "created_at": "2026-02-01T10:00:00Z",
                "last_activity": "2026-02-01T15:30:00Z",
                "expires_at": "2026-02-08T10:00:00Z",
                "is_active": True,
                "is_current": True,
            }
        }


class SessionListResponse(BaseModel):
    """List of all active sessions"""

    sessions: list[SessionResponse]
    total_count: int


class UserResponse(BaseModel):
    """User profile response"""

    user_id: str
    email: str
    username: str
    created_at: str
    is_active: bool


# Android message models
@dataclass
class AndroidMessage:
    """Message in Android conversation"""

    message_id: str  # UUID
    conversation_id: str  # Thread ID (user_id for now)
    user_id: str  # Owner of conversation
    sender: str  # "user" or "demi"
    content: str
    emotion_state: Optional[Dict[str, float]] = None
    status: str = "sent"  # sent, delivered, read
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "content": self.content,
            "emotion_state": self.emotion_state,
            "status": self.status,
            "delivered_at": self.delivered_at.isoformat()
            if self.delivered_at
            else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
        }


class SendMessageRequest(BaseModel):
    """Send message from Android client"""

    content: str


class MessageEvent(BaseModel):
    """WebSocket event"""

    event: str  # "message", "typing", "read_receipt"
    data: dict
