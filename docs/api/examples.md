# Code Examples

Practical code examples for common Demi API use cases.

## Table of Contents

- [Basic Bot Integration](#basic-bot-integration)
- [Custom Command Handler](#custom-command-handler)
- [Emotion Monitoring](#emotion-monitoring)
- [WebSocket Client](#websocket-client)
- [Complete Working Examples](#complete-working-examples)

---

## Basic Bot Integration

A minimal bot that connects to Demi and responds to messages.

### Python

```python
#!/usr/bin/env python3
"""Basic bot integration example."""

import asyncio
import os
from src.conductor import get_conductor
from src.core.config import DemiConfig
from src.platforms.base import PlatformIntegration

class BasicBot(PlatformIntegration):
    """Simple bot that forwards messages to/from Demi."""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = 'basic_bot'
    
    async def startup(self):
        print(f"✓ {self.name} started")
        return True
    
    async def shutdown(self):
        print(f"✓ {self.name} stopped")
    
    async def send_message(self, user_id: str, content: str):
        """Called when Demi wants to send a message."""
        print(f"[Demi -> {user_id}]: {content}")
    
    async def handle_message(self, user_id: str, content: str):
        """Handle incoming message from user."""
        # Send to Demi
        response = await self.conductor.request_inference_for_platform(
            platform=self.name,
            user_id=user_id,
            content=content,
            context={'timestamp': 'now'}
        )
        
        # Send response back
        await self.send_message(user_id, response['content'])


async def main():
    # Setup
    config = DemiConfig.load('src/core/defaults.yaml')
    conductor = get_conductor(config)
    
    bot = BasicBot(config)
    conductor.register_platform(bot)
    
    # Start
    await conductor.startup()
    
    # Simulate conversation
    await bot.handle_message('user-1', 'Hello Demi!')
    await bot.handle_message('user-1', 'How are you feeling today?')
    
    # Shutdown
    await conductor.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');
const WebSocket = require('ws');

class BasicBot {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
    this.ws = null;
  }

  async connect() {
    // Connect WebSocket
    const wsUrl = `${this.baseUrl.replace('http', 'ws')}/api/v1/chat/ws?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.on('open', () => {
      console.log('Connected to Demi');
    });

    this.ws.on('message', (data) => {
      const msg = JSON.parse(data);
      this.handleMessage(msg);
    });

    return new Promise((resolve) => {
      this.ws.once('open', resolve);
    });
  }

  handleMessage(msg) {
    switch (msg.event) {
      case 'message':
        console.log(`Demi: ${msg.data.content}`);
        break;
      case 'typing':
        console.log(msg.data.is_typing ? 'Demi is typing...' : '');
        break;
    }
  }

  sendMessage(content) {
    this.ws.send(JSON.stringify({
      event: 'message',
      data: { content }
    }));
  }

  disconnect() {
    this.ws.close();
  }
}

// Usage
async function main() {
  const bot = new BasicBot('http://localhost:8000', 'your-token');
  await bot.connect();
  
  bot.sendMessage('Hello Demi!');
  
  setTimeout(() => {
    bot.sendMessage('How are you?');
  }, 3000);
  
  setTimeout(() => {
    bot.disconnect();
    process.exit(0);
  }, 10000);
}

main().catch(console.error);
```

---

## Custom Command Handler

Bot with custom slash commands.

```python
#!/usr/bin/env python3
"""Bot with custom command handling."""

import asyncio
from src.conductor import get_conductor
from src.core.config import DemiConfig
from src.platforms.base import PlatformIntegration
from src.core.logger import get_logger

logger = get_logger()

class CommandBot(PlatformIntegration):
    """Bot that handles custom commands."""
    
    COMMANDS = {
        '/status': 'Show Demi\'s emotional state',
        '/mood': 'Get current mood',
        '/help': 'Show available commands',
        '/reset': 'Reset conversation context'
    }
    
    def __init__(self, config):
        super().__init__(config)
        self.name = 'command_bot'
    
    async def startup(self):
        logger.info("Command bot started")
        return True
    
    async def shutdown(self):
        logger.info("Command bot stopped")
    
    async def send_message(self, user_id: str, content: str):
        print(f"[Demi -> {user_id}]: {content}")
    
    async def handle_message(self, user_id: str, content: str):
        """Handle message with command parsing."""
        
        # Check if it's a command
        if content.startswith('/'):
            response = await self.handle_command(user_id, content)
        else:
            # Regular message - send to Demi
            result = await self.conductor.request_inference_for_platform(
                platform=self.name,
                user_id=user_id,
                content=content,
                context={'source': 'command_bot'}
            )
            response = result['content']
        
        await self.send_message(user_id, response)
    
    async def handle_command(self, user_id: str, command: str) -> str:
        """Process custom commands."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == '/help':
            return self._format_help()
        
        elif cmd == '/status':
            return await self._get_status()
        
        elif cmd == '/mood':
            return await self._get_mood()
        
        elif cmd == '/reset':
            # Clear conversation context
            return "Conversation context reset. What would you like to talk about?"
        
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."
    
    def _format_help(self) -> str:
        """Format help message."""
        lines = ["Available commands:"]
        for cmd, desc in self.COMMANDS.items():
            lines.append(f"  {cmd} - {desc}")
        return '\n'.join(lines)
    
    async def _get_status(self) -> str:
        """Get Demi's status."""
        try:
            from src.emotional.state import EmotionEngine
            engine = EmotionEngine()
            state = engine.get_current_state()
            
            return (
                f"Current emotional state:\n"
                f"  😊 Affection: {state.affection:.2f}\n"
                f"  😢 Loneliness: {state.loneliness:.2f}\n"
                f"  🤩 Excitement: {state.excitement:.2f}\n"
                f"  😤 Frustration: {state.frustration:.2f}\n"
                f"  😒 Jealousy: {state.jealousy:.2f}"
            )
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return "Sorry, I couldn't retrieve my status right now."
    
    async def _get_mood(self) -> str:
        """Get current mood."""
        # This would typically come from the emotional system
        moods = ['happy', 'sad', 'excited', 'lonely', 'chatty', 'grumpy']
        import random
        mood = random.choice(moods)
        return f"I'm feeling {mood} right now!"


async def main():
    config = DemiConfig.load('src/core/defaults.yaml')
    conductor = get_conductor(config)
    
    bot = CommandBot(config)
    conductor.register_platform(bot)
    
    await conductor.startup()
    
    # Test commands
    test_inputs = [
        '/help',
        '/status',
        '/mood',
        'Hello Demi!',
        '/unknown',
    ]
    
    for user_input in test_inputs:
        print(f"\n[User]: {user_input}")
        await bot.handle_message('user-1', user_input)
    
    await conductor.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
```

---

## Emotion Monitoring

Monitor and log Demi's emotional state over time.

```python
#!/usr/bin/env python3
"""Emotion monitoring tool."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.emotional.state import EmotionEngine
from src.emotion.persistence import EmotionPersistence
from src.core.logger import get_logger

logger = get_logger()

class EmotionMonitor:
    """Monitor and log emotional state changes."""
    
    def __init__(self, log_file: str = 'emotions.log'):
        self.log_file = Path(log_file)
        self.engine = EmotionEngine()
        self.persistence = EmotionPersistence()
        self.running = False
        self.thresholds = {
            'loneliness': 0.7,
            'excitement': 0.8,
            'frustration': 0.6,
        }
    
    async def start(self, interval: int = 60):
        """Start monitoring emotional state."""
        self.running = True
        logger.info(f"Starting emotion monitoring (interval: {interval}s)")
        
        # Load initial state
        state = await self.persistence.load_state()
        if state:
            self._log_state(state, 'initial')
        
        while self.running:
            try:
                # Get current state
                current = self.engine.get_current_state()
                
                # Check for threshold crossings
                alerts = self._check_thresholds(current)
                
                # Log state
                self._log_state(current, 'snapshot', alerts)
                
                # Wait for next check
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        logger.info("Emotion monitoring stopped")
    
    def _check_thresholds(self, state) -> list:
        """Check if any emotions crossed thresholds."""
        alerts = []
        for emotion, threshold in self.thresholds.items():
            value = getattr(state, emotion)
            if value >= threshold:
                alerts.append({
                    'emotion': emotion,
                    'value': value,
                    'threshold': threshold
                })
        return alerts
    
    def _log_state(self, state, event_type: str, alerts: list = None):
        """Log emotional state to file."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'state': {
                'loneliness': state.loneliness,
                'excitement': state.excitement,
                'frustration': state.frustration,
                'jealousy': state.jealousy,
                'affection': state.affection,
            },
            'alerts': alerts or []
        }
        
        # Append to log file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Log alerts
        if alerts:
            for alert in alerts:
                logger.warning(
                    f"Threshold alert: {alert['emotion']} = "
                    f"{alert['value']:.2f} (threshold: {alert['threshold']})"
                )
    
    def get_stats(self) -> dict:
        """Get statistics from log file."""
        if not self.log_file.exists():
            return {}
        
        states = []
        with open(self.log_file) as f:
            for line in f:
                entry = json.loads(line)
                if 'state' in entry:
                    states.append(entry['state'])
        
        if not states:
            return {}
        
        # Calculate averages and extremes
        stats = {}
        for emotion in ['loneliness', 'excitement', 'frustration', 'jealousy', 'affection']:
            values = [s[emotion] for s in states]
            stats[emotion] = {
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values),
                'current': values[-1]
            }
        
        return stats


async def main():
    monitor = EmotionMonitor('demi_emotions.log')
    
    # Run for 5 minutes
    task = asyncio.create_task(monitor.start(interval=10))
    
    try:
        await asyncio.sleep(300)  # 5 minutes
    finally:
        monitor.stop()
        await task
    
    # Print statistics
    stats = monitor.get_stats()
    print("\nEmotion Statistics:")
    for emotion, data in stats.items():
        print(f"  {emotion}:")
        print(f"    Current: {data['current']:.3f}")
        print(f"    Average: {data['avg']:.3f}")
        print(f"    Range: {data['min']:.3f} - {data['max']:.3f}")


if __name__ == '__main__':
    asyncio.run(main())
```

---

## WebSocket Client

Full-featured WebSocket client with reconnection.

```python
#!/usr/bin/env python3
"""WebSocket client with reconnection and message queueing."""

import asyncio
import json
import websockets
from dataclasses import dataclass, asdict
from typing import Callable, Optional
from datetime import datetime


@dataclass
class Message:
    message_id: str
    sender: str
    content: str
    timestamp: str
    emotion_state: Optional[dict] = None


class DemiWebSocketClient:
    """Production-ready WebSocket client."""
    
    def __init__(
        self,
        base_url: str,
        token: str,
        on_message: Optional[Callable[[Message], None]] = None,
        on_typing: Optional[Callable[[bool], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        self.base_url = base_url.replace('http', 'ws').replace('https', 'wss')
        self.token = token
        self.ws = None
        self.reconnect_attempts = 0
        self.max_reconnects = 5
        self.reconnect_delay = 1.0
        self.message_queue = []
        self.running = False
        
        # Callbacks
        self.on_message = on_message
        self.on_typing = on_typing
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error
    
    async def connect(self):
        """Connect with automatic reconnection."""
        self.running = True
        
        while self.running and self.reconnect_attempts < self.max_reconnects:
            try:
                uri = f"{self.base_url}/api/v1/chat/ws?token={self.token}"
                self.ws = await websockets.connect(uri)
                
                # Reset reconnection state
                self.reconnect_attempts = 0
                self.reconnect_delay = 1.0
                
                if self.on_connect:
                    self.on_connect()
                
                # Send queued messages
                await self._flush_queue()
                
                # Handle messages
                await self._handle_messages()
                
            except websockets.exceptions.InvalidStatusCode as e:
                if e.status_code == 1008:
                    if self.on_error:
                        self.on_error("Authentication failed - check your token")
                    self.running = False
                    return
                raise
            except Exception as e:
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= self.max_reconnects:
                    if self.on_error:
                        self.on_error(f"Max reconnection attempts reached: {e}")
                    self.running = False
                    return
                
                if self.on_disconnect:
                    self.on_disconnect()
                
                # Exponential backoff
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 30)
    
    async def _handle_messages(self):
        """Process incoming WebSocket messages."""
        try:
            async for message in self.ws:
                await self._process_message(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            if self.running:
                if self.on_disconnect:
                    self.on_disconnect()
    
    async def _process_message(self, msg: dict):
        """Route message to appropriate handler."""
        event = msg.get('event')
        data = msg.get('data', {})
        
        if event == 'message':
            message = Message(
                message_id=data.get('message_id'),
                sender=data.get('sender'),
                content=data.get('content'),
                timestamp=data.get('created_at'),
                emotion_state=data.get('emotion_state')
            )
            if self.on_message:
                self.on_message(message)
        
        elif event == 'typing':
            if self.on_typing:
                self.on_typing(data.get('is_typing', False))
        
        elif event == 'history':
            print(f"Loaded {data.get('count', 0)} historical messages")
        
        elif event == 'error':
            error_msg = data.get('message', 'Unknown error')
            if self.on_error:
                self.on_error(error_msg)
            else:
                print(f"Server error: {error_msg}")
    
    async def send(self, data: dict):
        """Send data to WebSocket."""
        if self.ws and self.ws.open:
            await self.ws.send(json.dumps(data))
        else:
            self.message_queue.append(data)
    
    async def send_message(self, content: str):
        """Send a chat message."""
        await self.send({
            'event': 'message',
            'data': {'content': content}
        })
    
    async def mark_read(self, message_id: str):
        """Mark a message as read."""
        await self.send({
            'event': 'read_receipt',
            'data': {'message_id': message_id}
        })
    
    async def ping(self):
        """Send keepalive ping."""
        await self.send({'event': 'ping'})
    
    async def _flush_queue(self):
        """Send queued messages."""
        while self.message_queue:
            msg = self.message_queue.pop(0)
            await self.ws.send(json.dumps(msg))
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self.running = False
        if self.ws:
            await self.ws.close()


# Example usage
async def interactive_chat():
    """Interactive chat session."""
    
    def on_message(msg: Message):
        print(f"\n[Demi]: {msg.content}")
        if msg.emotion_state:
            print(f"  (Affection: {msg.emotion_state.get('affection', 0):.2f})")
        print("\nYou: ", end='', flush=True)
    
    def on_typing(is_typing: bool):
        status = "typing..." if is_typing else "      "
        print(f"\rDemi is {status}", end='', flush=True)
    
    def on_connect():
        print("Connected to Demi!\n")
    
    def on_disconnect():
        print("\nDisconnected. Attempting to reconnect...")
    
    def on_error(error: str):
        print(f"\nError: {error}")
    
    # Create client
    client = DemiWebSocketClient(
        base_url='ws://localhost:8000',
        token='your-access-token',
        on_message=on_message,
        on_typing=on_typing,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_error=on_error
    )
    
    # Start connection
    asyncio.create_task(client.connect())
    
    # Interactive input
    await asyncio.sleep(1)  # Wait for connection
    
    try:
        while True:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, "You: "
            )
            
            if user_input.lower() in ('quit', 'exit'):
                break
            
            if user_input.strip():
                await client.send_message(user_input)
    
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(interactive_chat())
```

---

## Complete Working Examples

### API Authentication Flow

```python
#!/usr/bin/env python3
"""Complete authentication and API usage example."""

import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

class DemiAPIClient:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.session_id = None
    
    def login(self, email: str, password: str):
        """Authenticate and get tokens."""
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": email,
                "password": password,
                "device_name": "API Example"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.session_id = data["session_id"]
        self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
        
        print(f"✓ Logged in as {data['email']}")
        print(f"✓ Session ID: {self.session_id[:8]}...")
        return data
    
    def refresh(self):
        """Refresh access token."""
        response = requests.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        response.raise_for_status()
        data = response.json()
        
        self.access_token = data["access_token"]
        self.expires_at = datetime.now() + timedelta(seconds=data["expires_in"])
        
        print("✓ Token refreshed")
        return data
    
    def get_headers(self):
        """Get authorization headers."""
        if datetime.now() >= self.expires_at - timedelta(minutes=1):
            self.refresh()
        return {"Authorization": f"Bearer {self.access_token}"}
    
    def get_status(self):
        """Get system status."""
        response = requests.get(
            f"{BASE_URL}/status",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_sessions(self):
        """List active sessions."""
        response = requests.get(
            f"{BASE_URL}/auth/sessions",
            headers=self.get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def revoke_session(self, session_id: str):
        """Revoke a session."""
        response = requests.delete(
            f"{BASE_URL}/auth/sessions/{session_id}",
            headers=self.get_headers()
        )
        response.raise_for_status()
        print(f"✓ Revoked session {session_id[:8]}...")


def main():
    client = DemiAPIClient()
    
    # Login
    client.login("user@example.com", "password123")
    
    # Get status
    status = client.get_status()
    print(f"\nSystem Status: {status['status']}")
    if 'emotional_state' in status:
        print(f"Demi's mood: {status.get('current_mood', 'unknown')}")
    
    # List sessions
    sessions = client.get_sessions()
    print(f"\nActive Sessions: {sessions['total_count']}")
    for session in sessions['sessions']:
        marker = " (current)" if session['is_current'] else ""
        print(f"  - {session['device_name']}{marker}")
    
    # Get history via REST
    # (In production, use WebSocket for real-time messaging)


if __name__ == '__main__':
    main()
```

### Batch Message Sender

```python
#!/usr/bin/env python3
"""Send messages to multiple users."""

import asyncio
import aiohttp
from typing import List

async def send_to_user(
    session: aiohttp.ClientSession,
    base_url: str,
    token: str,
    user_id: str,
    message: str
):
    """Send message to a single user."""
    async with session.ws_connect(
        f"{base_url}/api/v1/chat/ws?token={token}"
    ) as ws:
        # Send message
        await ws.send_json({
            'event': 'message',
            'data': {'content': message}
        })
        
        # Wait for response
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.json()
                if data.get('event') == 'message':
                    return {
                        'user_id': user_id,
                        'response': data['data']['content']
                    }
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break
        
        return {'user_id': user_id, 'error': 'Connection error'}


async def broadcast(
    base_url: str,
    token: str,
    user_ids: List[str],
    message: str
):
    """Send message to multiple users concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_to_user(session, base_url, token, user_id, message)
            for user_id in user_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report results
        success = 0
        failed = 0
        
        for result in results:
            if isinstance(result, Exception):
                print(f"✗ Failed: {result}")
                failed += 1
            elif 'error' in result:
                print(f"✗ {result['user_id']}: {result['error']}")
                failed += 1
            else:
                print(f"✓ {result['user_id']}: {result['response'][:50]}...")
                success += 1
        
        print(f"\nTotal: {success} success, {failed} failed")


# Usage
# asyncio.run(broadcast('http://localhost:8000', 'token', ['user-1', 'user-2'], 'Hello!'))
```

### cURL Command Reference

```bash
#!/bin/bash
# Complete API workflow using cURL

BASE_URL="http://localhost:8000/api/v1"

# 1. Login
echo "=== Login ==="
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "device_name": "CLI Tool"
  }')

echo "Response: $LOGIN_RESP" | jq

ACCESS_TOKEN=$(echo $LOGIN_RESP | jq -r '.access_token')
REFRESH_TOKEN=$(echo $LOGIN_RESP | jq -r '.refresh_token')

# 2. Get Status
echo -e "\n=== Status ==="
curl -s "${BASE_URL}/status" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq

# 3. List Sessions
echo -e "\n=== Sessions ==="
SESSIONS=$(curl -s "${BASE_URL}/auth/sessions" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
echo $SESSIONS | jq

# 4. Refresh Token (demonstration)
echo -e "\n=== Refresh Token ==="
REFRESH_RESP=$(curl -s -X POST "${BASE_URL}/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"${REFRESH_TOKEN}\"}")
echo $REFRESH_RESP | jq '.access_token' | cut -c1-50
echo "..."

# 5. Get History
echo -e "\n=== Message History ==="
curl -s "${BASE_URL}/chat/history?limit=5" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | jq '.messages'

echo -e "\n=== Done ==="
```

---

## More Examples

See the `examples/` directory in the repository for:

- Discord bot integration
- Slack bot integration  
- Telegram bot integration
- Web dashboard
- Mobile app example
- Voice assistant integration

Each example includes:
- Complete source code
- Configuration files
- Setup instructions
- Usage examples
