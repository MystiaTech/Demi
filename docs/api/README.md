# Demi API Documentation

Welcome to the Demi API documentation. This guide provides everything you need to integrate with Demi, the AI companion with personality.

## Overview

Demi exposes multiple APIs for different use cases:

| API Type | Use Case | Protocol |
|----------|----------|----------|
| **REST API** | Authentication, status checks, message history | HTTP/JSON |
| **WebSocket API** | Real-time bidirectional messaging | WebSocket/JSON |
| **Python SDK** | Building custom integrations and extensions | Python 3.10+ |

## Quick Start

### 1. Get an Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'
```

### 2. Connect via WebSocket

```javascript
const token = 'your-access-token';
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws?token=${token}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Demi says:', data.data.content);
};

ws.onopen = () => {
  ws.send(JSON.stringify({
    event: 'message',
    data: { content: 'Hello Demi!' }
  }));
};
```

## Base URL

### Development
```
http://localhost:8000/api/v1
ws://localhost:8000/api/v1
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANDROID_API_HOST` | `0.0.0.0` | API server bind address |
| `ANDROID_API_PORT` | `8000` | API server port |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |

## Authentication

Demi uses JWT (JSON Web Token) authentication:

- **Access Token**: Short-lived (30 minutes), used for API requests
- **Refresh Token**: Long-lived (7 days), used to obtain new access tokens
- **Session Management**: Multi-device support with session listing/revocation

See [Authentication Guide](./authentication.md) for detailed flow.

### Using Tokens

Include the access token in the `Authorization` header:

```bash
curl http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer <your-access-token>"
```

For WebSocket, pass the token as a query parameter:

```
ws://localhost:8000/api/v1/chat/ws?token=<your-access-token>
```

## Rate Limiting

To ensure service stability, API requests are rate-limited:

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Authentication | 5 requests | 1 minute |
| General API | 100 requests | 1 minute |
| WebSocket | 50 messages | 1 minute |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706803200
```

## SDK Availability

### Official SDKs

| Language | Package | Status |
|----------|---------|--------|
| Python | `demi-client` | Planned |
| JavaScript | `demi-js` | Planned |

### Community SDKs

Community-maintained SDKs are available for:
- Rust
- Go
- TypeScript

## API Reference

### REST Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/login` | POST | No | Authenticate and get tokens |
| `/auth/refresh` | POST | No | Refresh access token |
| `/auth/sessions` | GET | Yes | List active sessions |
| `/auth/sessions/{id}` | DELETE | Yes | Revoke a session |
| `/status` | GET | No | System health check |
| `/chat/ws` | WebSocket | Yes | Real-time messaging |

See [REST API Reference](./rest-api.md) for complete documentation.

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `message` | Both | Send/receive messages |
| `typing` | Server | Typing indicator |
| `read_receipt` | Client | Mark message as read |
| `delivered` | Server | Message delivered confirmation |
| `history` | Server | Conversation history on connect |
| `ping/pong` | Both | Keepalive heartbeat |

See [WebSocket Protocol](./websocket.md) for detailed message formats.

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `200` | OK | Request successful |
| `201` | Created | Resource created successfully |
| `204` | No Content | Success, no body returned |
| `400` | Bad Request | Invalid request format |
| `401` | Unauthorized | Missing or invalid token |
| `403` | Forbidden | Account locked or disabled |
| `404` | Not Found | Resource doesn't exist |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

## Versioning

The current API version is **v1**. Version is included in the URL path:

```
/api/v1/status
```

When new versions are released, previous versions remain supported for at least 6 months.

## Documentation Index

- [Authentication Guide](./authentication.md) - JWT flows and session management
- [REST API Reference](./rest-api.md) - Complete endpoint documentation
- [WebSocket Protocol](./websocket.md) - Real-time messaging details
- [Python SDK](./python-sdk.md) - Python integration guide
- [Code Examples](./examples.md) - Working code samples

## Support

For API support:
- Open an issue on [GitHub](https://github.com/yourusername/demi)
- Check the [troubleshooting guide](../troubleshooting.md)
- Review [security considerations](../security.md)

## Changelog

### v1.0.0 (Current)
- Initial API release
- JWT authentication
- WebSocket real-time messaging
- Session management
- Autonomous check-ins
