# Demi Metrics System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Demi Components                             │
├─────────────────────────────────────────────────────────────────┤
│  LLM Inference         Platform Handlers       Emotion System    │
│  - chat()              - Discord              - update_state()   │
│  - process()           - Android              - record_emotion() │
│  - inference()         - Web                                     │
└──────────────┬──────────────────┬──────────────────┬─────────────┘
               │                  │                  │
               │ track_inference()│ track_message()  │ record_emotion_state()
               │                  │                  │
┌──────────────▼──────────────────▼──────────────────▼─────────────┐
│         Metrics Integration Layer (metrics_integration.py)        │
├──────────────────────────────────────────────────────────────────┤
│ - Context managers for automatic timing                          │
│ - Helper functions for recording metrics                         │
│ - Query helpers for retrieving historical data                   │
│ - Singleton accessors for specialized collectors                 │
└──────────────────────┬─────────────────────────────────────────┘
                       │
        ┌──────────────┴─────────────────┐
        │                                │
┌───────▼────────────────────┐  ┌────────▼────────────────────┐
│  Specialized Collectors    │  │   Base MetricsCollector     │
├────────────────────────────┤  ├─────────────────────────────┤
│ - LLMMetricsCollector      │  │ SQLite Storage              │
│ - PlatformMetricsCollector │  │ - Efficient indexing        │
│ - ConversationCollector    │  │ - Time-series support       │
│ - EmotionMetricsCollector  │  │ - Aggregation functions     │
│ - DiscordMetricsCollector  │  │ - Retention policies        │
└────────────┬────────────────┘  └────────┬──────────────────┘
             │                            │
             └────────────────┬───────────┘
                              │
                ┌─────────────▼─────────────┐
                │  SQLite Database          │
                │  ~/.demi/metrics.db       │
                │  - metrics table          │
                │  - indexes on name, time  │
                └───────────────────────────┘
```

## Data Flow

### Recording Metrics

```
Component (LLM/Platform/Emotion)
    ↓
Metrics Integration Layer (Context Manager)
    ↓
Specialized Collector (LLMMetrics, etc.)
    ↓
Base MetricsCollector
    ↓
SQLite Database
    ↓
WebSocket Broadcasting (via Dashboard Server)
```

### Retrieving Metrics

```
REST API Endpoint (/api/metrics/*)
    ↓
Dashboard Server
    ↓
Base MetricsCollector (get_metric, aggregate, etc.)
    ↓
SQLite Database
    ↓
JSON Response to Dashboard
    ↓
Dashboard JS (Chart.js Visualization)
```

## Component Details

### 1. Metrics Integration Layer
**File**: `src/monitoring/metrics_integration.py`

Provides:
- Context managers for automatic timing
- Helper functions for easy recording
- Query accessors for metric retrieval
- Global singleton pattern

Key Classes:
- `LLMInferenceMetrics` - Context manager for LLM tracking
- `PlatformMessageMetrics` - Context manager for platform tracking

Key Functions:
- `track_inference(model)` - Context manager for LLM inference
- `track_platform_message(platform)` - Context manager for messages
- `record_emotion_state(emotions)` - Record emotional state
- `record_conversation_turn(...)` - Record conversation metrics
- `update_discord_bot_status(...)` - Update Discord metrics

### 2. Specialized Collectors
**File**: `src/monitoring/metrics.py`

#### LLMMetricsCollector
Tracks:
- Response time (ms)
- Tokens generated
- Inference latency (ms)
- Prompt tokens
- Errors

Methods:
- `record_inference()` - Record inference operation
- `record_error()` - Record error
- Global accessor: `get_llm_metrics()`

#### PlatformMetricsCollector
Tracks:
- Message count per platform
- Response time per message
- Message length
- Error rate per platform

Methods:
- `record_message()` - Record message operation
- `get_platform_stats()` - Get aggregated stats
- Global accessor: `get_platform_metrics()`

#### ConversationMetricsCollector
Tracks:
- User message length
- Bot response length
- Conversation turn number
- Sentiment score

Methods:
- `record_conversation()` - Record conversation turn
- `get_quality_metrics()` - Get quality stats
- Global accessor: `get_conversation_metrics()`

#### EmotionMetricsCollector
Tracks (9 dimensions):
- loneliness, excitement, frustration
- jealousy, vulnerability, confidence
- curiosity, affection, defensiveness

Methods:
- `record_emotion_state()` - Record emotions
- `get_emotion_history()` - Get trend data
- `get_current_emotions()` - Get current state
- Global accessor: `get_emotion_metrics()`

#### DiscordMetricsCollector
Tracks:
- Online/offline status
- Latency (ms)
- Guild count
- Connected user count

Methods:
- `record_bot_status()` - Record status
- `get_bot_status()` - Get current status
- Global accessor: `get_discord_metrics()`

### 3. Base MetricsCollector
**File**: `src/monitoring/metrics.py` (existing, enhanced)

Features:
- SQLite persistence
- Time-series data storage
- Efficient indexing
- Aggregation functions (avg, min, max, sum, count)
- Configurable retention
- Automatic cleanup

Methods:
- `record()` - Record a metric
- `get_metric()` - Query metrics with time range
- `get_latest()` - Get most recent value
- `aggregate()` - Aggregate values (avg, min, max, sum, count)
- `cleanup_old_data()` - Remove old data
- Global accessor: `get_metrics_collector()`

### 4. Dashboard Server
**File**: `src/monitoring/dashboard_server.py` (enhanced)

New Endpoints:
- `GET /api/metrics/llm` - LLM performance stats
- `GET /api/metrics/platforms` - Platform stats
- `GET /api/metrics/conversation` - Conversation quality
- `GET /api/metrics/emotions/history` - Emotion history
- `GET /api/metrics/discord` - Discord bot status

Features:
- Real-time WebSocket updates
- REST API for metric queries
- Aggregation and filtering
- Error handling and logging

### 5. Dashboard Frontend
**Files**:
- `src/monitoring/dashboard_static/index.html` (enhanced)
- `src/monitoring/dashboard_static/dashboard.js` (enhanced)

New Sections:
1. Discord Bot Status Card
   - Online/offline indicator
   - Latency display
   - Guild and user counts

2. LLM Performance Card
   - Average response time
   - Max response time
   - Token count (1h)

3. Conversation Quality Card
   - User message length
   - Bot response length
   - Sentiment score
   - Max turn number

4. Emotion State Trend Chart
   - Line chart of emotion history
   - 9 emotion dimensions

5. Platform Metrics Card
   - Per-platform statistics
   - Error rates
   - Response times

New Methods:
- `fetchLLMMetrics()` / `updateLLMMetrics()`
- `fetchPlatformMetrics()` / `updatePlatformMetrics()`
- `fetchConversationMetrics()` / `updateConversationMetrics()`
- `fetchEmotionHistory()` / `updateEmotionHistory()` / `drawEmotionHistoryChart()`
- `fetchDiscordStatus()` / `updateDiscordStatus()`
- `startMetricsUpdates()` - 5-second update loop

## Database Schema

### Metrics Table
```sql
CREATE TABLE metrics (
    id TEXT PRIMARY KEY,                  -- UUID
    name TEXT NOT NULL,                   -- Metric name
    value REAL NOT NULL,                  -- Metric value
    metric_type TEXT NOT NULL,            -- counter/gauge/histogram
    timestamp REAL NOT NULL,              -- Unix timestamp
    labels TEXT DEFAULT '{}'              -- JSON labels
)

CREATE INDEX idx_metrics_name_time ON metrics(name, timestamp)
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp)
```

### Metric Names
```
# LLM Metrics
llm_response_time_ms
llm_tokens_generated
llm_inference_latency_ms
llm_prompt_tokens
llm_errors

# Platform Metrics
platform_{name}_messages
platform_{name}_response_time_ms
platform_{name}_message_length
platform_{name}_errors

# Conversation Metrics
conversation_user_message_length
conversation_bot_response_length
conversation_turn_number
conversation_sentiment

# Emotion Metrics
emotion_loneliness
emotion_excitement
emotion_frustration
emotion_jealousy
emotion_vulnerability
emotion_confidence
emotion_curiosity
emotion_affection
emotion_defensiveness

# Discord Metrics
discord_bot_online
discord_bot_latency_ms
discord_guild_count
discord_connected_users

# System Metrics (existing)
memory_percent
cpu_percent
disk_percent
response_time_p90
```

## Data Flow Examples

### Example 1: LLM Inference Tracking

```
1. Component calls: with track_inference("llama2"):
2. Context manager starts timer
3. LLM inference executes
4. Context manager calculates elapsed time
5. LLMMetricsCollector.record_inference() called
6. MetricsCollector.record() stores in SQLite
7. Callbacks notify WebSocket connections
8. Dashboard fetches /api/metrics/llm
9. Dashboard updates LLM Performance card
```

### Example 2: Emotion Recording

```
1. Component detects emotion change
2. Calls: record_emotion_state(emotions_dict)
3. EmotionMetricsCollector.record_emotion_state()
4. For each emotion:
   - MetricsCollector.record("emotion_{name}", value)
   - Stored in SQLite with timestamp
5. Dashboard fetches /api/metrics/emotions/history
6. Dashboard renders Emotion Trend chart
7. Chart shows historical emotion values
```

### Example 3: Platform Message Tracking

```
1. Message received on platform (Discord)
2. Handler wraps with: with track_platform_message("discord"):
3. Timer starts
4. Message processed
5. Timer stops, elapsed time calculated
6. PlatformMetricsCollector.record_message() called
7. Multiple metrics recorded:
   - platform_discord_messages (counter +1)
   - platform_discord_response_time_ms (timing)
   - platform_discord_message_length (size)
8. Dashboard fetches /api/metrics/platforms
9. Platform Metrics card updates with stats
```

## Integration Points

### 1. LLM Inference (src/llm/inference.py)
```python
with track_inference(self.config.model_name):
    response = await self._call_ollama(messages)
    metrics.set_tokens(prompt_tokens, response_tokens)
```

### 2. Platform Handlers (src/platforms/*.py)
```python
with track_platform_message(platform_name):
    response = await handle_message(msg)
    metrics.set_message_length(len(response))
```

### 3. Emotion Updates (src/emotion/persistence.py)
```python
record_emotion_state({
    "loneliness": state.loneliness,
    "excitement": state.excitement,
    # ... all emotions
})
```

### 4. Discord Bot (src/platforms/discord.py)
```python
# In periodic task (every 30s)
update_discord_bot_status(
    online=bot.is_ready(),
    latency_ms=bot.latency * 1000,
    guild_count=len(bot.guilds),
    connected_users=sum(len(g.members) for g in bot.guilds)
)
```

### 5. Conversation Tracking (message handler)
```python
record_conversation_turn(
    user_message_length=len(user_msg),
    bot_response_length=len(bot_response),
    turn_number=turn_count,
    sentiment_score=calculate_sentiment(user_msg)
)
```

## Real-Time Updates

```
Component records metric
    ↓
MetricsCollector broadcasts via registered callbacks
    ↓
Dashboard Server receives notification
    ↓
Dashboard Server broadcasts via WebSocket
    ↓
Dashboard JS receives update
    ↓
Dashboard updates visualization (5s cycle)
```

## Performance Characteristics

- **Recording**: O(1) insert into SQLite
- **Querying**: O(n) where n = number of points in time range
- **Aggregation**: O(n) with efficient SQL functions
- **Storage**: ~100 bytes per metric point
- **Update Latency**: <500ms from record to dashboard display

## Retention and Cleanup

Default: 7-day retention
- Older metrics automatically removed by `cleanup_old_data()`
- Called periodically during collection loop
- Configurable retention_days parameter

## Error Handling

```
Metric recording error
    ↓
Logger records error
    ↓
Exception caught in context manager
    ↓
Error metric recorded (if possible)
    ↓
Original exception propagated or suppressed based on context
```

## Extensibility

To add new metrics:

1. Create new collector class in `metrics.py`
2. Add global accessor function
3. Add endpoint in `dashboard_server.py`
4. Add dashboard section in `index.html`
5. Add fetch/update methods in `dashboard.js`

Example metric names follow pattern:
- `metric_type_category_dimension`
- e.g., `platform_discord_response_time_ms`
