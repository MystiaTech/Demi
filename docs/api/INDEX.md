# Demi API Documentation Index

This directory contains comprehensive API documentation for the Demi project.

## Files Overview

| File | Description | Lines |
|------|-------------|-------|
| [README.md](./README.md) | API Overview - Getting started, base URLs, authentication overview | 206 |
| [authentication.md](./authentication.md) | Authentication Guide - JWT flows, tokens, session management | 567 |
| [rest-api.md](./rest-api.md) | REST API Reference - All endpoint documentation | 552 |
| [websocket.md](./websocket.md) | WebSocket Protocol - Real-time messaging protocol | 675 |
| [python-sdk.md](./python-sdk.md) | Python SDK Documentation - SDK classes and integration | 676 |
| [examples.md](./examples.md) | Code Examples - Working examples in multiple languages | 973 |

## Quick Navigation

### Getting Started
1. Read [API Overview](./README.md) for introduction
2. Follow [Authentication Guide](./authentication.md) to get tokens
3. Use [REST API Reference](./rest-api.md) for HTTP endpoints
4. Check [WebSocket Protocol](./websocket.md) for real-time messaging

### Development
- [Python SDK](./python-sdk.md) for Python integrations
- [Code Examples](./examples.md) for copy-paste ready code

## Endpoints Covered

### Authentication
- `POST /api/v1/auth/login` - Authenticate and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/sessions` - List active sessions
- `DELETE /api/v1/auth/sessions/{id}` - Revoke a session

### Status
- `GET /api/v1/status` - System health check

### Messages (REST)
- `GET /api/v1/chat/history` - Get conversation history

### WebSocket
- `WS /api/v1/chat/ws` - Real-time bidirectional messaging

### Autonomy
- `GET /api/v1/autonomy/config` - Get autonomy configuration
- `GET /api/v1/autonomy/checkins` - Get check-in history

## Code Examples Available

- Basic bot integration (Python, JavaScript)
- Custom command handler (Python)
- Emotion monitoring tool (Python)
- WebSocket client with reconnection (Python, JavaScript)
- API authentication flow (Python, cURL)
- Batch message sender (Python)

## Languages Supported

- Python 3.10+
- JavaScript/Node.js
- cURL/bash
