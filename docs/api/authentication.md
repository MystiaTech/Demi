# Authentication Guide

This guide covers Demi's JWT-based authentication system, including login flows, token management, and security best practices.

## Overview

Demi uses JWT (JSON Web Tokens) for authentication with the following features:

- **Access Tokens**: Short-lived tokens (30 minutes) for API authentication
- **Refresh Tokens**: Long-lived tokens (7 days) for obtaining new access tokens
- **Session Management**: Multi-device support with ability to list and revoke sessions
- **Account Security**: Automatic lockout after failed login attempts

## Token Types

### Access Token

- **Lifetime**: 30 minutes
- **Usage**: Include in `Authorization: Bearer <token>` header
- **Contains**: User ID, email, session ID, expiration time
- **Secret**: Signed with `JWT_SECRET_KEY`

### Refresh Token

- **Lifetime**: 7 days
- **Usage**: Exchange for new access token via `/auth/refresh`
- **Contains**: User ID, session ID, expiration time
- **Secret**: Signed with `JWT_REFRESH_SECRET_KEY` (different from access token)

## Authentication Flow

### 1. Login

Exchange credentials for access and refresh tokens:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password",
    "device_name": "My Device",
    "device_fingerprint": "unique-device-id"
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_expires_in": 604800,
  "user_id": "uuid-1234",
  "email": "user@example.com",
  "session_id": "session-uuid-5678"
}
```

### 2. Use Access Token

Include the access token in API requests:

```bash
curl http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### 3. Refresh Token

When the access token expires (or before), get a new one:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }'
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_expires_in": 518400,
  "user_id": "uuid-1234",
  "email": "user@example.com",
  "session_id": "session-uuid-5678"
}
```

Note: The same refresh token is returned (it continues to work until expiry).

### 4. Logout (Revoke Session)

To log out from a specific device:

```bash
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/session-uuid-5678 \
  -H "Authorization: Bearer <access_token>"
```

## Token Expiration

### Access Token Expiration

Access tokens expire after 30 minutes. Handle expiration gracefully:

```python
import requests
from datetime import datetime, timedelta

class DemiAuth:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

    def is_token_expired(self):
        if not self.expires_at:
            return True
        # Refresh 60 seconds before actual expiration
        return datetime.now() >= self.expires_at - timedelta(seconds=60)

    async def ensure_valid_token(self):
        if self.is_token_expired():
            await self.refresh_access_token()

    async def refresh_access_token(self):
        response = requests.post(
            "http://localhost:8000/api/v1/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        data = response.json()
        self.access_token = data["access_token"]
        self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
```

### Refresh Token Expiration

Refresh tokens expire after 7 days of inactivity. When a refresh token expires:

1. The user must log in again with email/password
2. All sessions are effectively revoked
3. New access and refresh tokens are issued

## Session Management

### List Active Sessions

View all active sessions across devices:

```bash
curl http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer <access_token>"
```

**Response:**

```json
{
  "sessions": [
    {
      "session_id": "session-1234",
      "device_name": "Pixel 7",
      "created_at": "2026-02-01T10:00:00Z",
      "last_activity": "2026-02-01T15:30:00Z",
      "expires_at": "2026-02-08T10:00:00Z",
      "is_active": true,
      "is_current": true
    },
    {
      "session_id": "session-5678",
      "device_name": "Desktop Browser",
      "created_at": "2026-01-30T08:00:00Z",
      "last_activity": "2026-02-01T14:00:00Z",
      "expires_at": "2026-02-06T08:00:00Z",
      "is_active": true,
      "is_current": false
    }
  ],
  "total_count": 2
}
```

### Revoke Specific Session

Log out from a specific device remotely:

```bash
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/session-5678 \
  -H "Authorization: Bearer <access_token>"
```

### Revoke All Other Sessions

To implement "Log out everywhere else":

```python
async def logout_everywhere_else(access_token, current_session_id):
    # Get all sessions
    response = requests.get(
        "http://localhost:8000/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    sessions = response.json()["sessions"]

    # Revoke all except current
    for session in sessions:
        if not session["is_current"]:
            requests.delete(
                f"http://localhost:8000/api/v1/auth/sessions/{session['session_id']}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
```

## WebSocket Authentication

WebSocket connections authenticate via query parameter:

```javascript
const token = 'your-access-token';
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws?token=${token}`);
```

The token is validated during the WebSocket handshake. If invalid:

- Connection is closed with code `1008` (Policy Violation)
- Error reason is provided in close event

## Account Security

### Failed Login Attempts

- **Threshold**: 5 failed attempts
- **Lockout Duration**: 15 minutes
- **Reset**: Successful login resets counter

When locked:

```json
{
  "detail": "Account locked due to too many failed attempts. Try again after 2026-02-01T16:00:00Z"
}
```

### Security Best Practices

#### 1. Store Tokens Securely

**Web Applications:**
- Store access tokens in memory (not localStorage)
- Store refresh tokens in httpOnly cookies or secure storage
- Use CSRF protection for cookie-based storage

**Mobile Applications:**
- Use platform secure storage (Keychain on iOS, Keystore on Android)
- Encrypt tokens at rest
- Clear tokens on logout

#### 2. Handle Token Refresh

```python
import asyncio
import aiohttp
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self._lock = asyncio.Lock()

    async def get_valid_token(self):
        async with self._lock:
            if self._should_refresh():
                await self._refresh()
            return self.access_token

    def _should_refresh(self):
        if not self.expires_at:
            return True
        # Refresh 2 minutes before expiration
        return datetime.now() >= self.expires_at - timedelta(minutes=2)

    async def _refresh(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token}
            ) as response:
                data = await response.json()
                self.access_token = data["access_token"]
                self.expires_at = datetime.now() + timedelta(
                    seconds=data["expires_in"]
                )
```

#### 3. Validate HTTPS

Always use HTTPS in production:

```python
import ssl

# Verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED
```

#### 4. Secure Environment Variables

```bash
# .env file
JWT_SECRET_KEY=your-256-bit-secret-key-here
JWT_REFRESH_SECRET_KEY=different-256-bit-secret-key-here
```

Generate secure keys:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Code Examples

### Python

```python
import requests
from datetime import datetime, timedelta

class DemiAuthClient:
    BASE_URL = "http://localhost:8000/api/v1"

    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None

    def login(self, email: str, password: str) -> dict:
        """Authenticate and store tokens."""
        response = requests.post(
            f"{self.BASE_URL}/auth/login",
            json={
                "email": email,
                "password": password,
                "device_name": "Python Client"
            }
        )
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.expires_at = datetime.now() + timedelta(
            seconds=data["expires_in"]
        )

        return data

    def get_headers(self) -> dict:
        """Get authorization headers with valid token."""
        if datetime.now() >= self.expires_at - timedelta(minutes=1):
            self.refresh()
        return {"Authorization": f"Bearer {self.access_token}"}

    def refresh(self) -> dict:
        """Refresh access token."""
        response = requests.post(
            f"{self.BASE_URL}/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        response.raise_for_status()
        data = response.json()

        self.access_token = data["access_token"]
        self.expires_at = datetime.now() + timedelta(
            seconds=data["expires_in"]
        )

        return data

    def get_sessions(self) -> list:
        """List active sessions."""
        response = requests.get(
            f"{self.BASE_URL}/auth/sessions",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()["sessions"]

    def revoke_session(self, session_id: str):
        """Revoke a specific session."""
        response = requests.delete(
            f"{self.BASE_URL}/auth/sessions/{session_id}",
            headers=self.get_headers()
        )
        response.raise_for_status()


# Usage
client = DemiAuthClient()
client.login("user@example.com", "password123")
sessions = client.get_sessions()
print(f"Active sessions: {len(sessions)}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

class DemiAuthClient {
  constructor(baseUrl = 'http://localhost:8000/api/v1') {
    this.baseUrl = baseUrl;
    this.accessToken = null;
    this.refreshToken = null;
    this.expiresAt = null;
  }

  async login(email, password) {
    const response = await axios.post(`${this.baseUrl}/auth/login`, {
      email,
      password,
      device_name: 'Node.js Client'
    });

    const data = response.data;
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    this.expiresAt = Date.now() + (data.expires_in * 1000);

    return data;
  }

  async refresh() {
    const response = await axios.post(`${this.baseUrl}/auth/refresh`, {
      refresh_token: this.refreshToken
    });

    const data = response.data;
    this.accessToken = data.access_token;
    this.expiresAt = Date.now() + (data.expires_in * 1000);

    return data;
  }

  async getHeaders() {
    // Refresh if expiring in next 60 seconds
    if (Date.now() >= this.expiresAt - 60000) {
      await this.refresh();
    }
    return { Authorization: `Bearer ${this.accessToken}` };
  }

  async getSessions() {
    const headers = await this.getHeaders();
    const response = await axios.get(
      `${this.baseUrl}/auth/sessions`,
      { headers }
    );
    return response.data.sessions;
  }

  async revokeSession(sessionId) {
    const headers = await this.getHeaders();
    await axios.delete(
      `${this.baseUrl}/auth/sessions/${sessionId}`,
      { headers }
    );
  }
}

// Usage
async function main() {
  const client = new DemiAuthClient();
  await client.login('user@example.com', 'password123');
  
  const sessions = await client.getSessions();
  console.log(`Active sessions: ${sessions.length}`);
}

main().catch(console.error);
```

### cURL

```bash
# Login
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }')

# Extract tokens
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.refresh_token')

echo "Access Token: $ACCESS_TOKEN"

# Use token to get sessions
curl -s http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq

# Refresh token
REFRESH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}")

NEW_ACCESS_TOKEN=$(echo $REFRESH_RESPONSE | jq -r '.access_token')
echo "New Access Token: $NEW_ACCESS_TOKEN"
```

## Environment Setup

Required environment variables for authentication:

```bash
# Required: Secret keys for JWT signing
JWT_SECRET_KEY=your-256-bit-secret-key-minimum
JWT_REFRESH_SECRET_KEY=different-256-bit-secret-key-minimum

# Optional: Token lifetimes (defaults shown)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional: Security settings
MAX_FAILED_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
```

## Troubleshooting

### "Invalid token" Error

- Check token hasn't expired
- Verify token is complete (not truncated)
- Ensure `Authorization: Bearer <token>` format

### "Token expired" Error

- Use refresh token to get new access token
- Check system clock is synchronized
- Verify token expiration calculation

### "Account locked" Error

- Wait for lockout duration (15 minutes)
- Contact administrator if persistent
- Check for brute force attacks

### WebSocket Connection Closed (1008)

- Token is invalid or expired
- Re-authenticate and reconnect
- Check token is URL-encoded if needed
