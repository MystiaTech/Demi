# REST API Reference

Complete reference for all Demi REST API endpoints.

**Base URL:** `http://localhost:8000/api/v1`

---

## Authentication Endpoints

### POST /auth/login

Authenticate with email and password to receive access and refresh tokens.

**Authentication Required:** No

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User email address |
| `password` | string | Yes | User password |
| `device_name` | string | No | Device identifier (default: "Android Device") |
| `device_fingerprint` | string | No | Unique device ID |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MyPassword123!",
    "device_name": "Pixel 7",
    "device_fingerprint": "android-uuid-1234"
  }'
```

**Success Response (200):**

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

**Token Details:**

| Token | Duration | Usage |
|-------|----------|-------|
| `access_token` | 30 minutes | API authentication |
| `refresh_token` | 7 days | Obtain new access tokens |

**Error Responses:**

| Status | Code | Description |
|--------|------|-------------|
| `401` | `invalid_credentials` | Email or password is incorrect |
| `403` | `account_locked` | Account locked due to failed attempts |
| `403` | `account_disabled` | Account has been disabled |
| `400` | `validation_error` | Missing required fields |

**Account Lockout:**
- 5 failed login attempts locks account for 15 minutes
- Failed attempts reset on successful login

---

### POST /auth/refresh

Exchange a refresh token for a new access token.

**Authentication Required:** No (requires refresh token)

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | Valid refresh token |

**Example Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }'
```

**Success Response (200):**

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

**Error Responses:**

| Status | Description |
|--------|-------------|
| `401` | Invalid or expired refresh token |
| `401` | Session invalid or expired |

---

### GET /auth/sessions

List all active sessions for the authenticated user.

**Authentication Required:** Yes

**Example Request:**

```bash
curl http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer <access_token>"
```

**Success Response (200):**

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
      "device_name": "Galaxy Tab",
      "created_at": "2026-01-28T08:00:00Z",
      "last_activity": "2026-02-01T12:00:00Z",
      "expires_at": "2026-02-05T08:00:00Z",
      "is_active": true,
      "is_current": false
    }
  ],
  "total_count": 2
}
```

**Session Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier |
| `device_name` | string | Human-readable device name |
| `created_at` | string | ISO 8601 timestamp when session was created |
| `last_activity` | string | ISO 8601 timestamp of last activity |
| `expires_at` | string | ISO 8601 timestamp when session expires |
| `is_active` | boolean | Whether session is currently active |
| `is_current` | boolean | True if this is the current session |

**Error Responses:**

| Status | Description |
|--------|-------------|
| `401` | Missing or invalid access token |

---

### DELETE /auth/sessions/{session_id}

Revoke a specific session. Use this to log out from other devices.

**Authentication Required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | UUID of the session to revoke |

**Example Request:**

```bash
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/session-5678 \
  -H "Authorization: Bearer <access_token>"
```

**Success Response (200):**

```json
{
  "message": "Session revoked successfully"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| `401` | Missing or invalid access token |
| `404` | Session not found or not owned by user |

---

## Status Endpoints

### GET /status

Get Demi's current system status and health information.

**Authentication Required:** No (additional data if authenticated)

**Example Request:**

```bash
curl http://localhost:8000/api/v1/status
```

**Success Response (200) - Unauthenticated:**

```json
{
  "status": "ok",
  "service": "demi-android-api",
  "version": "1.0.0"
}
```

**Success Response (200) - Authenticated:**

When authenticated via header, additional emotional state data is included:

```json
{
  "status": "ok",
  "service": "demi-android-api",
  "version": "1.0.0",
  "emotional_state": {
    "loneliness": 0.35,
    "excitement": 0.72,
    "frustration": 0.11,
    "jealousy": 0.20,
    "affection": 0.68
  },
  "current_mood": "chatty"
}
```

**Emotional State Fields:**

| Field | Range | Description |
|-------|-------|-------------|
| `loneliness` | 0.0 - 1.0 | How lonely Demi feels |
| `excitement` | 0.0 - 1.0 | Current excitement level |
| `frustration` | 0.0 - 1.0 | Current frustration level |
| `jealousy` | 0.0 - 1.0 | Jealousy level |
| `affection` | 0.0 - 1.0 | Affection towards user |

---

## Message Endpoints

Messages are primarily handled via WebSocket for real-time communication. These REST endpoints provide polling alternatives and message history access.

### GET /chat/history

Get conversation history (REST alternative to WebSocket history event).

**Authentication Required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `conversation_id` | string | user_id | Conversation identifier |
| `days` | integer | 7 | Days of history to fetch |
| `limit` | integer | 100 | Maximum messages to return |
| `before` | string | - | ISO timestamp for pagination |

**Example Request:**

```bash
curl "http://localhost:8000/api/v1/chat/history?days=7&limit=50" \
  -H "Authorization: Bearer <access_token>"
```

**Success Response (200):**

```json
{
  "messages": [
    {
      "message_id": "msg-1234",
      "conversation_id": "user-uuid",
      "sender": "demi",
      "content": "How delightful that you seek my attention...",
      "emotion_state": {
        "loneliness": 0.25,
        "excitement": 0.60
      },
      "status": "read",
      "delivered_at": "2026-02-01T15:30:00Z",
      "read_at": "2026-02-01T15:31:00Z",
      "created_at": "2026-02-01T15:30:00Z"
    },
    {
      "message_id": "msg-5678",
      "conversation_id": "user-uuid",
      "sender": "user",
      "content": "Hello Demi!",
      "emotion_state": null,
      "status": "read",
      "delivered_at": "2026-02-01T15:29:00Z",
      "read_at": "2026-02-01T15:30:00Z",
      "created_at": "2026-02-01T15:29:00Z"
    }
  ],
  "has_more": true,
  "next_cursor": "2026-01-30T10:00:00Z"
}
```

**Message Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | string | Unique message identifier |
| `conversation_id` | string | Conversation this message belongs to |
| `sender` | string | `"user"` or `"demi"` |
| `content` | string | Message text content |
| `emotion_state` | object | Demi's emotions when sending (null for user messages) |
| `status` | string | `"sent"`, `"delivered"`, or `"read"` |
| `delivered_at` | string | ISO timestamp when delivered |
| `read_at` | string | ISO timestamp when read |
| `created_at` | string | ISO timestamp when created |

---

## Autonomy Endpoints

Autonomous check-ins allow Demi to initiate conversations based on her emotional state.

### GET /autonomy/config

Get autonomy system configuration and current triggers.

**Authentication Required:** Yes

**Example Request:**

```bash
curl http://localhost:8000/api/v1/autonomy/config \
  -H "Authorization: Bearer <access_token>"
```

**Success Response (200):**

```json
{
  "enabled": true,
  "check_interval_minutes": 15,
  "triggers": {
    "loneliness": {
      "threshold": 0.7,
      "message": "Hey, you there?"
    },
    "excitement": {
      "threshold": 0.8,
      "message": "OMG, guess what!"
    },
    "frustration": {
      "threshold": 0.6,
      "message": "Seriously?"
    }
  },
  "guilt_trip": {
    "enabled": true,
    "ignore_threshold_hours": 24
  }
}
```

---

### GET /autonomy/checkins

Get history of autonomous check-in messages.

**Authentication Required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum records to return |

**Example Request:**

```bash
curl "http://localhost:8000/api/v1/autonomy/checkins?limit=10" \
  -H "Authorization: Bearer <access_token>"
```

**Success Response (200):**

```json
{
  "checkins": [
    {
      "checkin_id": "checkin-1234",
      "trigger": "loneliness",
      "emotion_state": {
        "loneliness": 0.75,
        "excitement": 0.30
      },
      "was_ignored": false,
      "created_at": "2026-02-01T14:00:00Z"
    },
    {
      "checkin_id": "checkin-5678",
      "trigger": "guilt_trip",
      "emotion_state": {
        "loneliness": 0.80,
        "frustration": 0.65
      },
      "was_ignored": true,
      "created_at": "2026-01-30T10:00:00Z"
    }
  ],
  "total_count": 2
}
```

---

## Data Models

### User

```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "username": "username",
  "created_at": "2026-02-01T10:00:00Z",
  "is_active": true
}
```

### EmotionalState

```json
{
  "loneliness": 0.35,
  "excitement": 0.72,
  "frustration": 0.11,
  "jealousy": 0.20,
  "affection": 0.68
}
```

All emotion values are normalized floats between 0.0 and 1.0.

### Message

```json
{
  "message_id": "uuid-string",
  "conversation_id": "uuid-string",
  "sender": "user|demi",
  "content": "Message text",
  "emotion_state": { /* EmotionalState or null */ },
  "status": "sent|delivered|read",
  "delivered_at": "2026-02-01T15:30:00Z",
  "read_at": "2026-02-01T15:31:00Z",
  "created_at": "2026-02-01T15:29:00Z"
}
```

---

## Error Codes Reference

### HTTP Status Codes

| Code | Name | When to Use |
|------|------|-------------|
| `200` | OK | Successful GET, PUT, DELETE |
| `201` | Created | Successful POST creating resource |
| `204` | No Content | Successful DELETE with no body |
| `400` | Bad Request | Invalid JSON, missing fields |
| `401` | Unauthorized | Invalid or missing token |
| `403` | Forbidden | Account locked, permission denied |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |

### Common Error Messages

```json
{
  "detail": "Invalid email or password"
}
```

```json
{
  "detail": "Token expired"
}
```

```json
{
  "detail": "Account locked due to too many failed attempts. Try again after 2026-02-01T16:00:00Z"
}
```

```json
{
  "detail": "Session not found"
}
```

---

## API Versioning

The API is versioned via URL path:

```
/api/v1/status
/api/v2/status  # Future version
```

Current version: **v1.0.0**

Breaking changes will result in a new version. Deprecated endpoints will be marked and supported for 6 months.
