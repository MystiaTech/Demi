# Phase 06: Android Integration - Discovery

**Researched:** 2026-02-02  
**Research Scope:** FastAPI RESTful API design, JWT authentication, Android HTTP client patterns, push notifications (polling vs websockets), message persistence, user registration  
**Status:** Complete - Ready for planning

---

## Executive Summary

Phase 06 creates a REST API backend for Android clients to communicate with Demi. Research across FastAPI best practices, Android HTTP client patterns, and real-time notification strategies reveals:

1. **FastAPI** provides high-performance REST API with async/await, OpenAPI docs, automatic validation
2. **JWT authentication** secures endpoints via token-based auth (no sessions needed for mobile)
3. **Message endpoints** route through same LLM pipeline as Discord, differentiated by user_id
4. **Notification system** uses polling (simple) or websockets (real-time) for Demi-to-client push
5. **User registration** creates unique user_id, stores encrypted credentials, issues JWT tokens

---

## 1. FastAPI Architecture for Demi

### API Endpoint Structure

```
POST   /api/v1/auth/register     - Create new user account
POST   /api/v1/auth/login        - Authenticate, return JWT token
POST   /api/v1/messages/send     - Send message from Android → Demi
GET    /api/v1/messages/receive  - Poll for messages from Demi → Android
GET    /api/v1/notifications/poll - Poll for push notifications / new Demi messages
WS     /api/v1/chat/ws           - WebSocket for real-time bidirectional messaging (optional)
GET    /api/v1/status            - Health check
```

### FastAPI Skeleton

```python
# src/api/main.py

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt

app = FastAPI(title="Demi API", version="1.0.0")

# Authentication
security = HTTPBearer()

@app.post("/api/v1/auth/register")
async def register(email: str, password: str):
    # Hash password with bcrypt
    # Create user in DB with unique user_id
    # Return user_id + JWT token
    pass

@app.post("/api/v1/auth/login")
async def login(email: str, password: str):
    # Verify password against hash
    # Return JWT token
    pass

@app.post("/api/v1/messages/send")
async def send_message(
    credentials: HTTPAuthCredentials = Depends(security),
    content: str = ...
):
    # Verify JWT token
    # Extract user_id from token
    # Route through Conductor.request_inference(platform="android", user_id=user_id, content=content)
    # Return response
    pass

@app.get("/api/v1/messages/receive")
async def receive_messages(credentials: HTTPAuthCredentials = Depends(security)):
    # Verify JWT token
    # Extract user_id
    # Return last N unread messages from conversation history
    # Mark as read
    pass

@app.run(host="0.0.0.0", port=8000)
```

---

## 2. JWT Authentication

### Token Structure

```
Header: {"alg": "HS256", "typ": "JWT"}
Payload: {
  "user_id": "uuid-1234",
  "email": "user@example.com",
  "exp": 1704067200,  # 24 hours from now
  "iat": 1703980800
}
Signature: HMAC-SHA256(header.payload, secret_key)
```

### Implementation Pattern

```python
import jwt
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # User-provided, 32+ chars
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Password Security

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

---

## 3. Message Endpoints

### Send Message Flow

1. Android client sends: `POST /api/v1/messages/send`
   ```json
   {
     "content": "Hey, what's up?",
     "timestamp": "2026-02-02T15:30:00Z"
   }
   ```

2. Server verifies JWT, extracts user_id

3. Routes to Conductor:
   ```python
   response = await conductor.request_inference(
       platform="android",
       user_id=user_id,
       content=content,
       context={
           "timestamp": timestamp,
           "android_version": "13+",  # optional metadata
       }
   )
   ```

4. Returns response:
   ```json
   {
     "message_id": "msg-5678",
     "content": "Ha, being productive for once?",
     "emotion_state": {
       "loneliness": 0.3,
       "excitement": 0.8,
       ...
     },
     "timestamp": "2026-02-02T15:30:05Z"
   }
   ```

### Receive/Poll Messages Flow

Android apps can't receive push notifications without push service (Firebase Cloud Messaging). Two strategies:

**Strategy A: Polling (Simpler)**
- Android client polls `GET /api/v1/messages/receive` every 30 seconds
- Server returns array of new messages since last poll
- Client marks as read via `POST /api/v1/messages/read/{message_id}`
- Pros: Simple, no extra infrastructure
- Cons: Battery drain (frequent requests), latency (30-second window)
- Used for MVP (Phase 6)

**Strategy B: WebSocket (Real-time)**
- Upgrade HTTP connection to WebSocket `WS /api/v1/chat/ws`
- Server pushes messages immediately when generated
- Client receives notifications in real-time
- Pros: Battery-efficient (single connection), instant
- Cons: Complex (WebSocket management, reconnection logic)
- Deferred to Phase 2+ or optional

For Phase 06, implement Strategy A (polling). WebSocket as optional enhancement.

---

## 4. User Registration & Profile

### Registration Endpoint

```python
@app.post("/api/v1/auth/register")
async def register(
    email: str,
    password: str,
    username: Optional[str] = None
):
    # Validate email format
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email")
    
    # Check if email already registered
    if await db.user_exists(email):
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Validate password strength (12+ chars, mixed case, number)
    if not is_strong_password(password):
        raise HTTPException(status_code=400, detail="Password too weak")
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(password)
    user = User(
        user_id=user_id,
        email=email,
        username=username or email.split("@")[0],
        password_hash=hashed_password,
        created_at=datetime.utcnow()
    )
    await db.save(user)
    
    # Issue token
    token = create_access_token(user_id, email)
    
    return {
        "user_id": user_id,
        "email": email,
        "access_token": token,
        "token_type": "bearer"
    }
```

### User Database Schema

| Column | Type | Purpose |
|--------|------|---------|
| user_id | UUID | Unique identifier |
| email | VARCHAR(255) | Login credential (unique) |
| username | VARCHAR(50) | Display name |
| password_hash | VARCHAR(255) | bcrypt hash |
| created_at | TIMESTAMP | Account creation |
| last_login | TIMESTAMP | Last successful login |
| is_active | BOOLEAN | Account status |

---

## 5. Notification Strategy

### Polling Implementation (Phase 06)

Android client polls every 30 seconds:

```python
@app.get("/api/v1/notifications/poll")
async def poll_notifications(
    credentials: HTTPAuthCredentials = Depends(security)
):
    user_id = verify_token(credentials.credentials)["user_id"]
    
    # Get unread messages since last poll
    messages = await db.get_unread_messages(user_id)
    
    # Mark as read
    await db.mark_messages_read(user_id, [m.id for m in messages])
    
    return {
        "has_new_messages": len(messages) > 0,
        "messages": messages,
        "next_poll_interval_seconds": 30  # Client hint
    }
```

### Message Storage

Messages stored in `android_messages` table:

| Column | Type | Purpose |
|--------|------|---------|
| message_id | UUID | Unique ID |
| user_id | UUID | FK to user |
| direction | ENUM(sent, received) | Who sent |
| content | TEXT | Message body |
| emotion_state | JSON | Emotion at time of send |
| is_read | BOOLEAN | Read status |
| created_at | TIMESTAMP | Message time |

### Optional: WebSocket for Real-Time (Phase 2+)

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/api/v1/chat/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Verify token from ?token=... query param
    user_id = verify_token_from_query(websocket.query_params.get("token"))
    
    # Add to active connections
    active_connections.add((user_id, websocket))
    
    try:
        while True:
            # Receive message from Android client
            data = await websocket.receive_json()
            content = data.get("content")
            
            # Process through LLM pipeline
            response = await conductor.request_inference(
                platform="android",
                user_id=user_id,
                content=content
            )
            
            # Send back immediately
            await websocket.send_json({
                "message_id": response["message_id"],
                "content": response["content"]
            })
    except WebSocketDisconnect:
        active_connections.remove((user_id, websocket))
```

---

## 6. Integration with Conductor

### Platform Plugin for Android API

```python
# src/integrations/android_api.py

from src.platforms.base import BasePlatform
from fastapi import FastAPI

class AndroidAPI(BasePlatform):
    name = "android"
    
    async def initialize(self, conductor):
        self.conductor = conductor
        
        # Create FastAPI app
        self.app = FastAPI(title="Demi Android API")
        
        @self.app.post("/api/v1/messages/send")
        async def send_message(user_id: str, content: str):
            response = await conductor.request_inference(
                platform="android",
                user_id=user_id,
                content=content,
                context={"source": "android"}
            )
            # Store in android_messages table
            await self.db.store_message(
                user_id=user_id,
                direction="received",
                content=response["content"],
                emotion_state=response.get("emotion_state")
            )
            return response
        
        # Start server (handled by main.py)
    
    async def shutdown(self):
        # Stop FastAPI server
        pass
```

---

## 7. Error Handling & Rate Limiting

### Common Errors

| HTTP Code | Scenario | Response |
|-----------|----------|----------|
| 400 | Invalid email/password format | `{"error": "Invalid email format"}` |
| 401 | Missing/invalid JWT token | `{"error": "Unauthorized"}` |
| 409 | Email already registered | `{"error": "Email already registered"}` |
| 429 | Rate limit exceeded (10 requests/min per user) | `{"error": "Rate limited. Retry in 60s"}` |
| 500 | LLM inference timeout | `{"error": "Demi is thinking... try again"}` |

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/messages/send")
@limiter.limit("10/minute")  # 10 messages per minute per user
async def send_message(...):
    pass
```

---

## 8. API Documentation & Discovery

### OpenAPI/Swagger

FastAPI auto-generates OpenAPI schema at `/docs`:

```
GET /docs              → Swagger UI (interactive)
GET /redoc             → ReDoc UI (alternative)
GET /openapi.json      → Raw OpenAPI spec
```

### Android Client Library (Optional Phase 2)

Provide sample Android client (Kotlin/Java) with:
- Registration flow
- JWT token management
- Message send/receive
- Polling loop
- Error handling

---

## 9. Testing Strategy

### Unit Tests

- JWT token creation/verification
- Password hashing/verification
- Email validation
- Message endpoint routing
- Error handling (401, 409, etc.)

### Integration Tests

- Full registration → login → send message → receive response flow
- Concurrent message sends from multiple users
- Token expiration handling
- Rate limiting verification

### Load Tests

- 100 concurrent users, 10 messages/second total
- Verify message latency <3 seconds p90
- Verify no dropped messages

---

## 10. Environment Configuration

### Required Environment Variables

```bash
# JWT & Auth
JWT_SECRET_KEY="your-32+-char-secret"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_HOURS=24

# API Server
ANDROID_API_HOST="0.0.0.0"
ANDROID_API_PORT=8000
ANDROID_API_WORKERS=4

# Database
DATABASE_URL="sqlite:////home/user/.demi/demi.db"

# Rate Limiting
RATE_LIMIT_MESSAGES_PER_MINUTE=10
RATE_LIMIT_REGISTER_PER_HOUR=5
```

---

## Summary: Technology Choices

| Choice | Library | Version | Rationale |
|--------|---------|---------|-----------|
| API Framework | FastAPI | 0.104+ | Async, auto-validation, OpenAPI docs |
| Auth | JWT + bcrypt | pyjwt 2.8+ passlib 1.7+ | Stateless auth for mobile |
| Password Hashing | bcrypt | via passlib | Industry standard, slow (prevents brute force) |
| Rate Limiting | slowapi | 0.1.9+ | FastAPI-native, simple decorator-based |
| WebSocket (optional) | FastAPI native | Built-in | No extra dependency |
| CORS | fastapi.middleware.cors | Built-in | Allow Android client cross-origin |

---

## Known Unknowns / Risks

### Pre-Planning (Level 2-3)

- [ ] **Token expiration & refresh:** Should tokens expire at 24 hours or longer?
  - Action: Design refresh token flow (Plan 06-02)
  - Risk Level: MEDIUM

- [ ] **Message polling latency:** Will 30-second polling feel responsive to users?
  - Action: Phase 06 execution + user testing (Phase 9)
  - Risk Level: LOW (worst case: switch to 15-second polling, higher battery impact)

- [ ] **Concurrent message handling:** Can Conductor handle 10+ Android messages/second?
  - Action: Load test during Phase 06 (Plan 06-03)
  - Risk Level: MEDIUM (could force Conductor optimization)

- [ ] **Multi-device support:** Can user have multiple Android instances?
  - Decision: v1 supports single device per user (enforced via token revocation on new login)
  - Risk Level: LOW

---

## Setup Requirements

**For User (Phase 06 plan frontmatter):**

```yaml
user_setup:
  - service: android_api
    why: "FastAPI backend for Android client"
    env_vars:
      - name: JWT_SECRET_KEY
        source: "Generate: openssl rand -base64 32 (copy output)"
      - name: ANDROID_API_HOST
        source: "Set to 0.0.0.0 (listen on all interfaces)"
      - name: ANDROID_API_PORT
        source: "Set to 8000 (or desired port, must be accessible from Android device)"
```

---

