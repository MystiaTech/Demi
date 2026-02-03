# Python SDK Documentation

This guide covers the Python SDK for building custom integrations and extensions for Demi.

## Installation

```bash
# Conceptual package (not yet published)
pip install demi-client

# For now, use internal modules
from src.api.auth import get_current_user
from src.conductor import get_conductor
```

## Quick Start

```python
import asyncio
from src.conductor import get_conductor
from src.core.config import DemiConfig

async def main():
    # Load configuration
    config = DemiConfig.load('src/core/defaults.yaml')
    
    # Initialize conductor
    conductor = get_conductor(config)
    
    # Start the system
    await conductor.startup()
    
    # Request inference
    response = await conductor.request_inference_for_platform(
        platform='custom_integration',
        user_id='user-123',
        content='Hello Demi!',
        context={'source': 'my_bot'}
    )
    
    print(f"Demi: {response['content']}")
    
    # Shutdown
    await conductor.shutdown()

asyncio.run(main())
```

## Core Modules

### Configuration (`src.core.config`)

Manage Demi's configuration settings.

```python
from src.core.config import DemiConfig

# Load configuration
config = DemiConfig.load('path/to/config.yaml')

# Access settings
print(config.system['log_level'])
print(config.platforms['discord']['enabled'])

# Get nested values with defaults
debug_mode = config.system.get('debug', False)

# Runtime updates
config.update('system', 'log_level', 'DEBUG')

# Access as dictionary
config_dict = config.to_dict()
```

**Key Configuration Sections:**

| Section | Description |
|---------|-------------|
| `system` | Core system settings (log_level, debug) |
| `platforms` | Platform-specific configurations |
| `llm` | Language model settings |
| `emotions` | Emotional system configuration |
| `autonomy` | Autonomous behavior settings |

### Logger (`src.core.logger`)

Structured logging with automatic context.

```python
from src.core.logger import get_logger, DemiLogger

# Get logger instance
logger = get_logger()

# Standard log levels
logger.debug("Debug information")
logger.info("Application started")
logger.warning("Something might be wrong")
logger.error("An error occurred")

# Structured logging with context
logger.info("User action", extra={
    'user_id': 'user-123',
    'action': 'send_message',
    'platform': 'discord'
})
```

### Conductor (`src.conductor`)

Central orchestrator for all Demi operations.

```python
from src.conductor import get_conductor

conductor = get_conductor(config)

# Lifecycle
await conductor.startup()
await conductor.shutdown()

# Check status
if conductor.is_running():
    print("Conductor is running")

# Request inference
response = await conductor.request_inference_for_platform(
    platform='custom_integration',
    user_id='user-123',
    content='Hello!',
    context={
        'source': 'custom_bot',
        'conversation_id': 'conv-456'
    }
)

# Response format
print(response['content'])  # Generated text
print(response['emotion_state'])  # Emotional state snapshot
```

### Emotional System (`src.emotional`)

Access and manipulate Demi's emotional state.

```python
from src.emotional.state import EmotionEngine
from src.emotion.persistence import EmotionPersistence

# Create engine instance
engine = EmotionEngine()

# Get current state
state = engine.get_current_state()
print(f"Loneliness: {state.loneliness}")
print(f"Excitement: {state.excitement}")

# Trigger emotional updates
engine.on_interaction(positive=True)   # Positive interaction
engine.on_interaction(positive=False)  # Negative interaction
engine.on_error_occurred()             # Error happened
engine.on_message_received()           # Message received
engine.on_long_wait()                  # User took long to respond

# Persist state
await EmotionPersistence.save_state(state)

# Load state
loaded_state = await EmotionPersistence.load_state()
```

**Emotional State Attributes:**

| Attribute | Range | Description |
|-----------|-------|-------------|
| `loneliness` | 0.0 - 1.0 | How lonely Demi feels |
| `excitement` | 0.0 - 1.0 | Current excitement level |
| `frustration` | 0.0 - 1.0 | Frustration level |
| `jealousy` | 0.0 - 1.0 | Jealousy towards other AIs/people |
| `affection` | 0.0 - 1.0 | Affection towards user |

### Database Access (`src.database`)

SQLite database for persistence.

```python
from src.database.connection import get_db

async with get_db() as db:
    # Query emotional state
    state = await db.get_emotional_state()
    
    # Log interaction
    await db.log_interaction(
        platform='custom',
        user_id='user-123',
        content='Hello',
        emotion_snapshot=state.to_dict()
    )
    
    # Get conversation history
    messages = await db.get_conversation_history(
        user_id='user-123',
        limit=50
    )
```

### LLM Client (`src.llm`)

Direct access to language models.

```python
from src.llm.client import LLMClient

client = LLMClient(config.llm)

# Generate response
response = await client.generate(
    prompt="Tell me a joke",
    system_prompt="You are a helpful assistant",
    temperature=0.7,
    max_tokens=150
)

print(response['content'])

# Streaming (if supported)
async for chunk in client.generate_stream(
    prompt="Tell me a story",
    system_prompt="You are a storyteller"
):
    print(chunk, end='')
```

## Building Custom Integrations

### Creating a Platform Integration

Extend `PlatformIntegration` to add new platforms:

```python
from src.platforms.base import PlatformIntegration
from src.core.logger import get_logger

logger = get_logger()

class CustomIntegration(PlatformIntegration):
    def __init__(self, config):
        super().__init__(config)
        self.name = 'custom_platform'
        self.client = None
    
    async def startup(self):
        """Initialize platform connection."""
        try:
            # Initialize your platform client
            self.client = await self._connect()
            logger.info(f"{self.name} platform started")
            return True
        except Exception as e:
            logger.error(f"Failed to start {self.name}: {e}")
            return False
    
    async def shutdown(self):
        """Cleanup platform resources."""
        if self.client:
            await self.client.disconnect()
        logger.info(f"{self.name} platform stopped")
    
    async def send_message(self, user_id: str, content: str):
        """Send a message to a user."""
        try:
            await self.client.send_message(user_id, content)
            logger.debug(f"Message sent to {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def handle_incoming(self, message):
        """Process incoming message."""
        # Extract info from your platform's message format
        user_id = message.user_id
        content = message.content
        
        # Request inference from Demi
        response = await self.conductor.request_inference_for_platform(
            platform=self.name,
            user_id=user_id,
            content=content,
            context={
                'source': self.name,
                'message_id': message.id
            }
        )
        
        # Send response back
        await self.send_message(user_id, response['content'])
    
    async def is_available(self) -> bool:
        """Check if platform is available."""
        return self.client is not None and self.client.is_connected()
```

### Registering Your Integration

```python
from src.conductor import get_conductor
from src.core.config import DemiConfig

async def main():
    config = DemiConfig.load('config.yaml')
    conductor = get_conductor(config)
    
    # Create and register your integration
    custom = CustomIntegration(config)
    conductor.register_platform(custom)
    
    # Start everything
    await conductor.startup()
    
    # Run until shutdown
    try:
        while conductor.is_running():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await conductor.shutdown()

asyncio.run(main())
```

## Async/Await Patterns

### Concurrent Operations

```python
import asyncio

async def handle_multiple_users(user_ids: list, message: str):
    """Send message to multiple users concurrently."""
    tasks = [
        send_to_user(user_id, message)
        for user_id in user_ids
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle results
    for user_id, result in zip(user_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to send to {user_id}: {result}")
        else:
            logger.info(f"Sent to {user_id}")

async def send_to_user(user_id: str, message: str):
    """Send message to single user."""
    # Your sending logic here
    await asyncio.sleep(0.1)  # Simulate work
    return True
```

### Timeouts

```python
async def request_with_timeout():
    """Request with timeout protection."""
    try:
        response = await asyncio.wait_for(
            conductor.request_inference_for_platform(
                platform='custom',
                user_id='user-123',
                content='Hello'
            ),
            timeout=30.0  # 30 second timeout
        )
        return response
    except asyncio.TimeoutError:
        logger.error("Request timed out")
        return {'content': 'Sorry, I took too long to respond.'}
```

### Semaphores

```python
# Limit concurrent operations
semaphore = asyncio.Semaphore(10)

async def limited_operation():
    async with semaphore:
        # Only 10 of these will run concurrently
        return await some_expensive_operation()
```

## Error Handling

### Try/Except Patterns

```python
from src.api.auth import HTTPException

async def safe_api_call():
    try:
        result = await risky_operation()
        return result
    except HTTPException as e:
        # API-specific errors
        logger.error(f"API error {e.status_code}: {e.detail}")
        raise
    except ConnectionError as e:
        # Network errors
        logger.error(f"Connection failed: {e}")
        return None
    except Exception as e:
        # Unexpected errors
        logger.exception("Unexpected error")
        raise
```

### Context Managers

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_resource():
    """Context manager for resource cleanup."""
    resource = await create_resource()
    try:
        yield resource
    finally:
        await resource.cleanup()

# Usage
async with managed_resource() as resource:
    await resource.do_work()
# Cleanup happens automatically
```

## Testing

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_custom_integration():
    # Mock dependencies
    mock_config = MagicMock()
    mock_conductor = AsyncMock()
    
    # Create integration
    integration = CustomIntegration(mock_config)
    integration.conductor = mock_conductor
    
    # Test startup
    result = await integration.startup()
    assert result is True
    
    # Test message handling
    mock_conductor.request_inference_for_platform.return_value = {
        'content': 'Hello!'
    }
    
    await integration.handle_incoming(
        MagicMock(user_id='user-123', content='Hi')
    )
    
    mock_conductor.request_inference_for_platform.assert_called_once()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_flow():
    # Use test configuration
    config = DemiConfig.load('tests/fixtures/test_config.yaml')
    
    conductor = get_conductor(config)
    await conductor.startup()
    
    try:
        # Test inference
        response = await conductor.request_inference_for_platform(
            platform='test',
            user_id='test-user',
            content='Test message'
        )
        
        assert 'content' in response
        assert len(response['content']) > 0
        
    finally:
        await conductor.shutdown()
```

## Best Practices

### 1. Always Use Type Hints

```python
from typing import Optional, Dict, Any

async def process_message(
    user_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ...
```

### 2. Document Your Code

```python
async def send_notification(
    user_id: str,
    message: str,
    priority: str = 'normal'
) -> bool:
    """
    Send notification to a user.
    
    Args:
        user_id: Target user identifier
        message: Notification content
        priority: 'low', 'normal', or 'high'
    
    Returns:
        True if sent successfully, False otherwise
    
    Raises:
        ValueError: If priority is invalid
    """
    if priority not in ('low', 'normal', 'high'):
        raise ValueError(f"Invalid priority: {priority}")
    # ... implementation
```

### 3. Use Structured Logging

```python
# Good
logger.info("Message sent", extra={
    'user_id': user_id,
    'platform': platform,
    'message_length': len(content)
})

# Avoid
logger.info(f"Sent message to {user_id} on {platform}")
```

### 4. Handle Cleanup Properly

```python
async def process_with_cleanup():
    temp_file = None
    try:
        temp_file = await create_temp_file()
        await process_file(temp_file)
    finally:
        if temp_file:
            await cleanup_temp_file(temp_file)
```

## Full Example: Custom Bot

```python
#!/usr/bin/env python3
"""
Example custom bot integration for Demi.
"""

import asyncio
import signal
from src.conductor import get_conductor
from src.core.config import DemiConfig
from src.core.logger import get_logger
from src.platforms.base import PlatformIntegration

logger = get_logger()

class SimpleBot(PlatformIntegration):
    """Simple command-line bot for testing."""
    
    def __init__(self, config):
        super().__init__(config)
        self.name = 'simple_bot'
        self.running = False
    
    async def startup(self):
        self.running = True
        logger.info("Simple bot started. Type messages to chat with Demi.")
        logger.info("Type 'quit' to exit.")
        
        # Start input loop in background
        asyncio.create_task(self._input_loop())
        return True
    
    async def shutdown(self):
        self.running = False
        logger.info("Simple bot stopped")
    
    async def _input_loop(self):
        """Read user input and send to Demi."""
        while self.running:
            try:
                # Get input (run in thread to not block)
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(
                    None, input, "You: "
                )
                
                if user_input.lower() == 'quit':
                    await self.shutdown()
                    break
                
                if user_input.strip():
                    await self._process_input(user_input)
                    
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Input error: {e}")
    
    async def _process_input(self, content: str):
        """Process user input and get response."""
        response = await self.conductor.request_inference_for_platform(
            platform=self.name,
            user_id='cli-user',
            content=content,
            context={'source': 'cli'}
        )
        
        print(f"Demi: {response['content']}")
    
    async def send_message(self, user_id: str, content: str):
        """Display message to user."""
        print(f"Demi: {content}")


async def main():
    # Load config
    config = DemiConfig.load('src/core/defaults.yaml')
    
    # Create conductor and bot
    conductor = get_conductor(config)
    bot = SimpleBot(config)
    conductor.register_platform(bot)
    
    # Handle shutdown signals
    def handle_signal():
        asyncio.create_task(conductor.shutdown())
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)
    
    # Start
    await conductor.startup()
    
    # Wait for shutdown
    while conductor.is_running():
        await asyncio.sleep(0.1)


if __name__ == '__main__':
    asyncio.run(main())
```

Run the bot:

```bash
python simple_bot.py
```
