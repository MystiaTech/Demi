# Demi Comprehensive Metrics Collection System

## Overview

Demi now includes a comprehensive metrics collection and dashboard system for real-time monitoring of:

- **LLM Performance**: Response times, tokens generated, inference latency
- **Platform Statistics**: Message counts, response times, error rates by platform
- **Conversation Quality**: Message lengths, sentiment scores, turn tracking
- **Emotional State**: Historical emotion values with trends
- **Discord Bot Status**: Online status, latency, guild count, user count

## Architecture

### Backend Components

#### 1. **MetricsCollector** (`src/monitoring/metrics.py`)
Core metrics storage using SQLite with time-series data support:
- Records metrics with timestamps
- Supports aggregation (avg, min, max, sum, count)
- Configurable retention policy
- JSON persistence

#### 2. **Specialized Collectors**

```python
# LLM Metrics
from src.monitoring.metrics import get_llm_metrics
llm_metrics = get_llm_metrics()
llm_metrics.record_inference(
    response_time_ms=150.5,
    tokens_generated=256,
    inference_latency_ms=120.0,
    prompt_tokens=100
)

# Platform Metrics
from src.monitoring.metrics import get_platform_metrics
platform_metrics = get_platform_metrics()
platform_metrics.record_message(
    platform="discord",
    response_time_ms=50.0,
    message_length=150,
    success=True
)

# Emotion Metrics
from src.monitoring.metrics import get_emotion_metrics
emotion_metrics = get_emotion_metrics()
emotion_metrics.record_emotion_state({
    "loneliness": 0.3,
    "excitement": 0.7,
    "frustration": 0.2,
    # ... other emotions
})

# Conversation Metrics
from src.monitoring.metrics import get_conversation_metrics
conv_metrics = get_conversation_metrics()
conv_metrics.record_conversation(
    user_message_length=50,
    bot_response_length=150,
    conversation_turn=5,
    sentiment_score=0.75
)

# Discord Metrics
from src.monitoring.metrics import get_discord_metrics
discord_metrics = get_discord_metrics()
discord_metrics.record_bot_status(
    online=True,
    latency_ms=45.0,
    guild_count=15,
    connected_users=230
)
```

#### 3. **Integration Helpers** (`src/monitoring/metrics_integration.py`)
Convenient context managers and helpers for integration:

```python
from src.monitoring.metrics_integration import (
    track_inference,
    track_platform_message,
    record_emotion_state,
    record_conversation_turn,
    update_discord_bot_status,
)

# Track LLM inference with automatic timing
with track_inference("llama2") as metrics:
    response = await llm.chat(messages)
    metrics.set_tokens(prompt_tokens=100, response_tokens=256)

# Track platform messages
with track_platform_message("discord") as metrics:
    response = await send_message(channel, text)
    metrics.set_message_length(len(text))

# Record emotions
record_emotion_state({
    "loneliness": 0.3,
    "excitement": 0.7,
    # ...
})

# Record conversation
record_conversation_turn(
    user_message_length=50,
    bot_response_length=150,
    turn_number=5
)

# Update Discord status
update_discord_bot_status(
    online=True,
    latency_ms=45.0,
    guild_count=15,
    connected_users=230
)
```

### REST API Endpoints

#### Health and Alerts
- `GET /api/health` - Overall system health
- `GET /api/alerts` - Active and historical alerts
- `POST /api/alerts/{id}/ack` - Acknowledge alert
- `POST /api/alerts/{id}/resolve` - Resolve alert

#### LLM Metrics
- `GET /api/metrics/llm` - LLM performance stats
  - Response times (last hour)
  - Tokens generated
  - Inference latencies
  - Statistics (avg, max, total)

#### Platform Metrics
- `GET /api/metrics/platforms` - Platform interaction stats
  - Message counts per platform
  - Average response times
  - Error counts and rates

#### Conversation Metrics
- `GET /api/metrics/conversation` - Conversation quality
  - Average message lengths
  - Sentiment trends
  - Turn counts

#### Emotion Metrics
- `GET /api/metrics/emotions` - Current emotional state
- `GET /api/metrics/emotions/history` - Emotional state history
  - Query parameters: `hours` (default 1), `limit` (default 100)
  - Returns time-series data for all emotions

#### Discord Metrics
- `GET /api/metrics/discord` - Discord bot status
  - Online/offline status
  - Latency
  - Guild and user counts

### WebSocket Updates

Real-time updates via `/ws` endpoint:
```json
{
  "type": "update",
  "timestamp": "2024-02-03T18:00:00Z",
  "metrics": {
    "memory_percent": 45.2,
    "cpu_percent": 25.0,
    "disk_percent": 60.0,
    "response_time_p90": 150.0
  },
  "emotions": {
    "loneliness": 0.3,
    "excitement": 0.7,
    ...
  },
  "alerts": [...]
}
```

## Dashboard Features

### Real-Time Visualization

1. **System Health Overview**
   - Current status (Healthy/Warning/Critical)
   - Memory, CPU, Disk usage with visual bars
   - Color-coded thresholds

2. **Discord Bot Status Card**
   - Online/offline indicator with animated pulse
   - Latency display
   - Guild and user counts

3. **LLM Performance Metrics**
   - Average response time
   - Maximum response time
   - Token count (1-hour window)

4. **Conversation Quality**
   - Average user message length
   - Average response length
   - Sentiment score
   - Maximum conversation turn

5. **Emotion State Visualization**
   - Radar chart for current emotions
   - Legend with values and color coding
   - Trend chart showing emotion history

6. **Platform Status**
   - Status indicators for each platform
   - Health color coding

7. **Platform Metrics Chart**
   - Message counts per platform
   - Response times
   - Error rates

## Integration Examples

### LLM Inference Integration

```python
# In src/llm/inference.py
from src.monitoring.metrics_integration import track_inference

async def chat(self, messages, ...):
    with track_inference(self.config.model_name) as metrics:
        # Your inference logic
        response = await self._call_ollama(messages)

        # Set token counts if available
        if hasattr(response, 'prompt_tokens'):
            metrics.set_tokens(
                prompt_tokens=response.prompt_tokens,
                response_tokens=len(response.split())
            )

        return response
```

### Platform Message Handlers

```python
# In platform handlers (Discord, Android, etc.)
from src.monitoring.metrics_integration import track_platform_message

async def handle_message(message):
    with track_platform_message("discord") as metrics:
        # Your message handling logic
        response = await process_and_respond(message)
        metrics.set_message_length(len(response))
        return response
```

### Emotion State Updates

```python
# In src/emotion/persistence.py or emotion modulators
from src.monitoring.metrics_integration import record_emotion_state

def update_emotional_state(new_state):
    # Store in persistence...
    persistence.save(new_state)

    # Record metrics
    record_emotion_state({
        "loneliness": new_state.loneliness,
        "excitement": new_state.excitement,
        "frustration": new_state.frustration,
        # ... all emotions
    })
```

### Discord Bot Status

```python
# In Discord bot status monitor
from src.monitoring.metrics_integration import update_discord_bot_status

async def update_bot_metrics():
    bot_status = {
        "online": bot.is_ready(),
        "latency_ms": bot.latency * 1000,
        "guild_count": len(bot.guilds),
        "connected_users": sum(len(guild.members) for guild in bot.guilds)
    }

    update_discord_bot_status(**bot_status)
```

## Configuration

### Metrics Retention

```python
from src.monitoring.metrics import MetricsCollector

collector = MetricsCollector(
    db_path="~/.demi/metrics.db",
    retention_days=7,  # Keep 7 days of data
    collection_interval=30  # Collect system metrics every 30s
)
```

### Dashboard Server

```python
from src.monitoring.dashboard_server import DashboardServer

server = DashboardServer(
    host="0.0.0.0",
    port=8080,
    update_interval=5,  # Send updates every 5 seconds
    api_key="your-optional-key"
)
```

## Storage

All metrics are stored in SQLite at `~/.demi/metrics.db` with:
- Timestamp indexing for efficient queries
- Metric name indexing
- Configurable retention policy
- Automatic cleanup of old data

## Performance Considerations

1. **Database**: SQLite is optimized for time-series data with proper indexing
2. **Update Frequency**: WebSocket updates every 5 seconds (configurable)
3. **History Limits**: Default 100 points per metric to keep dashboard responsive
4. **Retention**: 7 days of data by default (configurable)

## Monitoring Health

Use the dashboard to monitor:

1. **Resource Usage**: Memory, CPU, disk
2. **LLM Health**: Response times, token usage
3. **Platform Health**: Message rates, error rates
4. **Conversation Health**: Message lengths, sentiment
5. **Emotion Stability**: Emotion trends over time
6. **Bot Health**: Discord connectivity and performance

## Customization

### Adding New Metrics

```python
from src.monitoring.metrics import get_metrics_collector, MetricType

collector = get_metrics_collector()

# Record a gauge metric
collector.record(
    name="custom_metric",
    value=42.0,
    metric_type=MetricType.GAUGE,
    labels={"source": "my_component"}
)

# Query metrics
metrics = collector.get_metric("custom_metric", limit=100)
latest = collector.get_latest("custom_metric")
aggregated = collector.aggregate("custom_metric", "avg")
```

### Custom Dashboard Cards

Edit `src/monitoring/dashboard_static/index.html` to add new sections and update `dashboard.js` with fetch and render methods.

## Troubleshooting

### Metrics Not Showing
1. Check database exists: `~/.demi/metrics.db`
2. Verify metrics are being recorded: Check logs for integration points
3. Restart dashboard server to refresh

### High Memory Usage
1. Reduce retention period: `retention_days=3`
2. Reduce collection interval: `collection_interval=60`
3. Manually cleanup: Call `collector.cleanup_old_data()`

### Slow Dashboard
1. Reduce history limit in API queries
2. Increase WebSocket update interval
3. Clear old metrics data

## API Key Security

Protect the dashboard with an API key:

```python
server = DashboardServer(
    api_key="your-secret-key-here"
)
```

Or set via environment variable:
```bash
export DEMI_DASHBOARD_API_KEY="your-secret-key-here"
```

## Future Enhancements

Potential additions:
- Prometheus export format
- Custom alert rules based on metrics
- Historical comparisons and anomaly detection
- Performance trending and predictions
- Integration with external monitoring systems
