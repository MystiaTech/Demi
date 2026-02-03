# WebSocket Protocol

This document describes Demi's WebSocket protocol for real-time bidirectional messaging.

## Overview

The WebSocket API provides:

- **Real-time messaging**: Instant message delivery in both directions
- **Typing indicators**: Show when Demi is typing
- **Delivery confirmations**: Know when messages are delivered and read
- **Conversation history**: Automatic history sync on connection
- **Emotion updates**: Real-time emotional state changes
- **Autonomous messages**: Demi-initiated check-ins

## Connection

### Endpoint

```
ws://localhost:8000/api/v1/chat/ws?token=<access_token>
```

### Authentication

Pass the JWT access token as a query parameter:

```javascript
const token = 'your-access-token';
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws?token=${token}`);
```

If authentication fails, the connection is closed with code `1008` (Policy Violation).

### Connection Lifecycle

```
┌─────────────┐
│   Connect   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Authenticate│◄── Invalid token → Close(1008)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Send History│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Message Loop│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Disconnect  │
└─────────────┘
```

## Message Format

All messages are JSON with the following structure:

```json
{
  "event": "event_name",
  "data": { /* event-specific data */ },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Event type identifier |
| `data` | object | Event-specific payload |
| `timestamp` | string | ISO 8601 timestamp (server-generated) |

## Client-to-Server Events

These events are sent by the client to Demi.

### message

Send a message to Demi.

```json
{
  "event": "message",
  "data": {
    "content": "Hello Demi! How are you today?"
  }
}
```

**Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Message text (max 4000 characters) |

**Notes:**
- Empty content is ignored
- Rate limited: 50 messages per minute
- Response is sent via server `message` event

### read_receipt

Mark a message as read.

```json
{
  "event": "read_receipt",
  "data": {
    "message_id": "msg-uuid-1234"
  }
}
```

**Data Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message_id` | string | Yes | ID of message to mark as read |

### ping

Keepalive ping (optional - clients should still send).

```json
{
  "event": "ping"
}
```

Server responds with `pong` event.

## Server-to-Client Events

These events are sent by Demi to the client.

### history

Sent immediately after successful connection. Contains recent conversation history.

```json
{
  "event": "history",
  "data": {
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
    "count": 50
  },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

**Data Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `messages` | array | Array of message objects (chronological order) |
| `count` | integer | Number of messages included |

### message

Demi's response to a user message or autonomous check-in.

```json
{
  "event": "message",
  "data": {
    "message_id": "msg-uuid-5678",
    "conversation_id": "conv-uuid",
    "sender": "demi",
    "content": "How delightful that you seek my attention. I'm actually doing quite well, thank you for asking!",
    "emotion_state": {
      "loneliness": 0.20,
      "excitement": 0.65,
      "frustration": 0.05,
      "jealousy": 0.15,
      "affection": 0.70
    },
    "status": "sent",
    "delivered_at": null,
    "read_at": null,
    "created_at": "2026-02-01T15:30:00Z"
  },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

**Data Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | string | Unique message identifier |
| `conversation_id` | string | Conversation this message belongs to |
| `sender` | string | Always `"demi"` |
| `content` | string | Message text content |
| `emotion_state` | object | Demi's emotional state when sending |
| `status` | string | `"sent"`, `"delivered"`, or `"read"` |
| `created_at` | string | ISO 8601 timestamp |

### typing

Typing indicator from Demi.

```json
{
  "event": "typing",
  "data": {
    "is_typing": true
  },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

**Data Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `is_typing` | boolean | `true` when typing starts, `false` when ends |

**Timing:**
- Typing starts immediately after user message
- Typing ends when response is ready (typically 0.5-3 seconds)

### delivered

Confirmation that a message was delivered to Demi.

```json
{
  "event": "delivered",
  "data": {
    "message_id": "msg-uuid-1234"
  },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

Sent immediately after user message is received and stored.

### pong

Keepalive response to client ping.

```json
{
  "event": "pong",
  "timestamp": "2026-02-01T15:30:00Z"
}
```

### error

Error message from server.

```json
{
  "event": "error",
  "data": {
    "message": "Error generating response",
    "code": "inference_error"
  },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

**Error Codes:**

| Code | Description |
|------|-------------|
| `inference_error` | LLM failed to generate response |
| `rate_limited` | Too many messages sent |
| `invalid_message` | Message format invalid |
| `server_error` | Internal server error |

### emotion_update

Real-time emotional state update (if subscribed).

```json
{
  "event": "emotion_update",
  "data": {
    "loneliness": 0.45,
    "excitement": 0.30,
    "frustration": 0.20,
    "jealousy": 0.15,
    "affection": 0.55,
    "mood": "neutral"
  },
  "timestamp": "2026-02-01T15:30:00Z"
}
```

## Reconnection Handling

WebSocket connections can drop. Implement reconnection logic:

```javascript
class DemiWebSocketClient {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.messageQueue = [];
    this.onMessage = null;
    this.onTyping = null;
    this.onConnect = null;
  }

  connect() {
    const url = `${this.baseUrl}/api/v1/chat/ws?token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('Connected to Demi');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      
      // Send queued messages
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift();
        this.send(msg);
      }
      
      if (this.onConnect) this.onConnect();
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };

    this.ws.onclose = (event) => {
      console.log('Disconnected:', event.code, event.reason);
      
      // Don't reconnect if authentication failed
      if (event.code === 1008) {
        console.error('Authentication failed - not reconnecting');
        return;
      }
      
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  handleMessage(msg) {
    switch (msg.event) {
      case 'message':
        if (this.onMessage) this.onMessage(msg.data);
        break;
      case 'typing':
        if (this.onTyping) this.onTyping(msg.data.is_typing);
        break;
      case 'history':
        console.log(`Loaded ${msg.data.count} historical messages`);
        break;
      case 'error':
        console.error('Server error:', msg.data.message);
        break;
    }
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      this.messageQueue.push(data);
    }
  }

  sendMessage(content) {
    this.send({
      event: 'message',
      data: { content }
    });
  }

  markAsRead(messageId) {
    this.send({
      event: 'read_receipt',
      data: { message_id: messageId }
    });
  }

  ping() {
    this.send({ event: 'ping' });
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Reconnecting... attempt ${this.reconnectAttempts}`);

    setTimeout(() => {
      this.connect();
      // Exponential backoff
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    }, this.reconnectDelay);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Usage
const client = new DemiWebSocketClient('ws://localhost:8000', 'your-token');

client.onMessage = (msg) => {
  console.log('Demi:', msg.content);
  client.markAsRead(msg.message_id);
};

client.onTyping = (isTyping) => {
  console.log(isTyping ? 'Demi is typing...' : '');
};

client.onConnect = () => {
  client.sendMessage('Hello Demi!');
};

client.connect();
```

## Heartbeat/Ping-Pong

Keep connections alive with periodic pings:

```javascript
// Send ping every 30 seconds
const pingInterval = setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ event: 'ping' }));
  }
}, 30000);

// Clean up on disconnect
ws.onclose = () => {
  clearInterval(pingInterval);
};
```

## Complete Python Example

```python
import asyncio
import json
import websockets

class DemiWebSocketClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.replace('http', 'ws')
        self.token = token
        self.ws = None
        self.reconnect_attempts = 0
        self.max_reconnects = 5
        self.message_handlers = {}

    def on(self, event: str, handler):
        """Register event handler."""
        self.message_handlers[event] = handler

    async def connect(self):
        """Connect to WebSocket with reconnection."""
        uri = f"{self.base_url}/api/v1/chat/ws?token={self.token}"
        
        while self.reconnect_attempts < self.max_reconnects:
            try:
                self.ws = await websockets.connect(uri)
                self.reconnect_attempts = 0
                print("Connected to Demi")
                
                # Start message handler
                await self._handle_messages()
                
            except websockets.exceptions.InvalidStatusCode as e:
                if e.status_code == 1008:
                    print("Authentication failed - check your token")
                    return
                raise
            except Exception as e:
                self.reconnect_attempts += 1
                wait_time = min(2 ** self.reconnect_attempts, 30)
                print(f"Connection failed: {e}")
                print(f"Reconnecting in {wait_time}s... (attempt {self.reconnect_attempts})")
                await asyncio.sleep(wait_time)

    async def _handle_messages(self):
        """Handle incoming messages."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                event = data.get('event')
                
                handler = self.message_handlers.get(event)
                if handler:
                    handler(data.get('data'))
                
                # Default handlers
                if event == 'history':
                    print(f"Loaded {data['data']['count']} messages")
                elif event == 'typing':
                    status = "typing..." if data['data']['is_typing'] else ""
                    print(f"\rDemi {status}", end='', flush=True)
                elif event == 'error':
                    print(f"Error: {data['data']['message']}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection closed")

    async def send_message(self, content: str):
        """Send a message to Demi."""
        if self.ws:
            await self.ws.send(json.dumps({
                'event': 'message',
                'data': {'content': content}
            }))

    async def mark_read(self, message_id: str):
        """Mark a message as read."""
        if self.ws:
            await self.ws.send(json.dumps({
                'event': 'read_receipt',
                'data': {'message_id': message_id}
            }))

    async def ping(self):
        """Send keepalive ping."""
        if self.ws:
            await self.ws.send(json.dumps({'event': 'ping'}))

    async def close(self):
        """Close connection."""
        if self.ws:
            await self.ws.close()


# Usage
async def main():
    client = DemiWebSocketClient('ws://localhost:8000', 'your-token')
    
    # Register handlers
    client.on('message', lambda data: print(f"\nDemi: {data['content']}"))
    
    # Connect
    await client.connect()
    
    # Send messages
    await client.send_message("Hello Demi!")
    await asyncio.sleep(5)
    await client.send_message("How are you feeling?")
    
    # Keep alive
    await asyncio.sleep(30)
    await client.close()

asyncio.run(main())
```

## Error Handling

### Connection Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `1008` | Invalid token | Re-authenticate |
| `1011` | Server error | Retry after delay |
| `1006` | Connection lost | Reconnect with backoff |

### Message Errors

Handle errors gracefully:

```javascript
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.event === 'error') {
    console.error('Server error:', msg.data.message);
    
    switch (msg.data.code) {
      case 'rate_limited':
        // Back off and retry
        setTimeout(() => sendMessage(lastMessage), 5000);
        break;
      case 'inference_error':
        // Show error to user
        displayError('Demi is having trouble responding. Please try again.');
        break;
      default:
        displayError('Something went wrong. Please try again.');
    }
  }
};
```

## Rate Limiting

WebSocket messages are rate-limited:

- **Message sending**: 50 messages per minute
- **Ping frequency**: Minimum 10 seconds between pings

Exceeding limits results in `rate_limited` error event.

## Autonomous Messages

Demi can send messages without user input (check-ins):

```json
{
  "event": "message",
  "data": {
    "message_id": "msg-checkin-1234",
    "sender": "demi",
    "content": "Hey, you there? I'm feeling a bit lonely...",
    "emotion_state": {
      "loneliness": 0.75
    },
    "created_at": "2026-02-01T15:30:00Z"
  }
}
```

These are triggered by:
- Loneliness > 0.7
- Excitement > 0.8
- Frustration > 0.6
- User hasn't responded in 24+ hours (guilt trip)
