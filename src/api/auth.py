from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
import jwt
import os
import uuid
import sqlite3
import json
from typing import Optional
from passlib.context import CryptContext

from src.api.models import (
    User,
    Session,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    SessionResponse,
    SessionListResponse,
)
from src.core.logger import DemiLogger

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer()
logger = DemiLogger()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")

# Validate secrets are set
if not SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable must be set. "
        "Generate a secure random key: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
if not REFRESH_SECRET_KEY:
    raise ValueError(
        "JWT_REFRESH_SECRET_KEY environment variable must be set. "
        "Generate a secure random key: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_path() -> str:
    """Get database path"""
    db_url = os.getenv("DATABASE_URL", "sqlite:////home/user/.demi/demi.db")
    return db_url.replace("sqlite:///", "")


def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str, session_id: str) -> str:
    """Create short-lived access token (30 minutes)"""
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "session_id": session_id,
        "type": "access",
        "exp": int(exp.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def create_refresh_token(user_id: str, session_id: str) -> str:
    """Create long-lived refresh token (7 days)"""
    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "type": "refresh",
        "exp": int(exp.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    token = jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify JWT token, return payload"""
    try:
        secret = SECRET_KEY if token_type == "access" else REFRESH_SECRET_KEY
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])

        # Verify token type matches
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail=f"Invalid {token_type} token")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependency to get current user from access token"""
    token = credentials.credentials
    return verify_token(token, token_type="access")


async def get_user_from_db(email: str) -> Optional[User]:
    """Query user by email"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not row:
        return None

    return User(
        user_id=row["user_id"],
        email=row["email"],
        username=row["username"],
        password_hash=row["password_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_login=datetime.fromisoformat(row["last_login"])
        if row["last_login"]
        else None,
        is_active=bool(row["is_active"]),
        failed_login_attempts=row["failed_login_attempts"],
        locked_until=datetime.fromisoformat(row["locked_until"])
        if row["locked_until"]
        else None,
    )


async def create_session(
    user_id: str,
    device_name: str,
    device_fingerprint: Optional[str],
    refresh_token: str,
) -> Session:
    """Create new session for device"""
    session_id = str(uuid.uuid4())
    refresh_token_hash = hash_password(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    session = Session(
        session_id=session_id,
        user_id=user_id,
        device_name=device_name,
        device_fingerprint=device_fingerprint or "",
        refresh_token_hash=refresh_token_hash,
        created_at=datetime.now(timezone.utc),
        last_activity=datetime.now(timezone.utc),
        expires_at=expires_at,
        is_active=True,
    )

    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        INSERT INTO sessions
        (session_id, user_id, device_name, device_fingerprint, refresh_token_hash,
         created_at, last_activity, expires_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                session.session_id,
                session.user_id,
                session.device_name,
                session.device_fingerprint,
                session.refresh_token_hash,
                session.created_at.isoformat(),
                session.last_activity.isoformat(),
                session.expires_at.isoformat(),
                session.is_active,
            ),
        )
        conn.commit()

    logger.info(f"Session created (user_id: {user_id})")
    return session


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """
    Login with existing account credentials.
    Returns access token (30 min) and refresh token (7 days).
    """

    # Get user from DB
    user = await get_user_from_db(req.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=403,
            detail=f"Account locked due to too many failed attempts. Try again after {user.locked_until.isoformat()}",
        )

    # Verify password
    if not verify_password(req.password, user.password_hash):
        # Increment failed attempts
        db_path = get_db_path()
        with sqlite3.connect(db_path) as conn:
            new_failed_attempts = user.failed_login_attempts + 1

            # Lock account after 5 failed attempts
            locked_until = None
            if new_failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )
                logger.warning(f"Account locked: {user.email} (5 failed attempts)")

            conn.execute(
                """
            UPDATE users
            SET failed_login_attempts = ?, locked_until = ?
            WHERE user_id = ?
            """,
                (
                    new_failed_attempts,
                    locked_until.isoformat() if locked_until else None,
                    user.user_id,
                ),
            )
            conn.commit()

        if new_failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            logger.warning(f"Account locked: too many failed attempts (user_id: {user.user_id})")

        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Reset failed login attempts on successful login
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        UPDATE users
        SET last_login = ?, failed_login_attempts = 0, locked_until = NULL
        WHERE user_id = ?
        """,
            (datetime.now(timezone.utc).isoformat(), user.user_id),
        )
        conn.commit()

    # Create session
    refresh_token = create_refresh_token(user.user_id, "temp-session-id")
    session = await create_session(
        user_id=user.user_id,
        device_name=req.device_name,
        device_fingerprint=req.device_fingerprint,
        refresh_token=refresh_token,
    )

    # Issue tokens
    access_token = create_access_token(user.user_id, user.email, session.session_id)
    refresh_token = create_refresh_token(user.user_id, session.session_id)

    logger.info(f"User login successful (session_id: {session.session_id[-8:]})")  # Log last 8 chars only

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        user_id=user.user_id,
        email=user.email,
        session_id=session.session_id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(req: RefreshTokenRequest):
    """
    Exchange refresh token for new access token.
    Refresh token must be valid and session must be active.
    """

    # Verify refresh token
    payload = verify_token(req.refresh_token, token_type="refresh")
    session_id = payload.get("session_id")
    user_id = payload.get("user_id")

    # Get session from DB
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()

    if not row or not row["is_active"]:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    # Check expiry
    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    # Update last activity
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
            (datetime.now(timezone.utc).isoformat(), session_id),
        )
        conn.commit()

    # Get user email for access token
    user = await get_user_from_db_by_id(user_id)

    # Issue new access token
    access_token = create_access_token(user_id, user.email, session_id)

    logger.info(f"Access token refreshed (session_id: {session_id[-8:]})")  # Log last 8 chars only

    return TokenResponse(
        access_token=access_token,
        refresh_token=req.refresh_token,  # Return same refresh token
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_expires_in=int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        user_id=user_id,
        email=user.email,
        session_id=session_id,
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(current_user: dict = Depends(get_current_user)):
    """
    List all active sessions for current user across all devices.
    Shows device name, created time, last activity, expiry.
    """
    user_id = current_user["user_id"]
    current_session_id = current_user["session_id"]

    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
        SELECT * FROM sessions
        WHERE user_id = ? AND is_active = 1 AND expires_at > ?
        ORDER BY last_activity DESC
        """,
            (user_id, datetime.now(timezone.utc).isoformat()),
        ).fetchall()

    sessions = []
    for row in rows:
        sessions.append(
            SessionResponse(
                session_id=row["session_id"],
                device_name=row["device_name"],
                created_at=row["created_at"],
                last_activity=row["last_activity"],
                expires_at=row["expires_at"],
                is_active=bool(row["is_active"]),
                is_current=(row["session_id"] == current_session_id),
            )
        )

    return SessionListResponse(sessions=sessions, total_count=len(sessions))


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Revoke specific session/device (multi-device support).
    User can remotely logout from other devices.
    """
    user_id = current_user["user_id"]

    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        # Verify session belongs to user
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

        if not row or row[0] != user_id:
            raise HTTPException(status_code=404, detail="Session not found")

        # Revoke session
        conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,)
        )
        conn.commit()

    logger.info(f"Session revoked (session_id: {session_id[-8:]}, user_id: {user_id[:8]})")  # Log last 8 chars only

    return {"message": "Session revoked successfully"}


async def get_user_from_db_by_id(user_id: str) -> User:
    """Query user by ID"""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        user_id=row["user_id"],
        email=row["email"],
        username=row["username"],
        password_hash=row["password_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_login=datetime.fromisoformat(row["last_login"])
        if row["last_login"]
        else None,
        is_active=bool(row["is_active"]),
        failed_login_attempts=row["failed_login_attempts"],
        locked_until=datetime.fromisoformat(row["locked_until"])
        if row["locked_until"]
        else None,
    )
