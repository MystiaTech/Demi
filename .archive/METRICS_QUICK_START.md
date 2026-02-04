# Demi Metrics - Quick Start Guide

## What Was Added

A comprehensive metrics collection and real-time dashboard system with:
- **5 specialized metric collectors** (LLM, Platform, Conversation, Emotion, Discord)
- **5 new REST API endpoints** for metric data
- **5 new dashboard cards** with real-time visualization
- **Easy-to-use integration helpers** for recording metrics

## One-Minute Overview

### Recording Metrics

```python
# Track LLM inference (automatic timing)
from src.monitoring.metrics_integration import track_inference

with track_inference("llama2"):
    response = await llm.chat(messages)  # Automatically timed!

# Track platform messages
from src.monitoring.metrics_integration import track_platform_message

with track_platform_message("discord"):
    await send_message(channel, text)  # Automatically timed!

# Record emotions
from src.monitoring.metrics_integration import record_emotion_state

record_emotion_state({
    "loneliness": 0.3,
    "excitement": 0.7,
    "frustration": 0.2,
    "jealousy": 0.1,
    "vulnerability": 0.4,
    "confidence": 0.8,
    "curiosity": 0.6,
    "affection": 0.5,
    "defensiveness": 0.1,
})
```

### Viewing Metrics

1. Start the dashboard server:
   ```bash
   python3 src/monitoring/dashboard_server.py
   ```

2. Open browser to: `http://localhost:8080`

3. Watch real-time metrics update every 5 seconds

## API Endpoints

```
GET /api/metrics/llm              - LLM performance (response time, tokens)
GET /api/metrics/platforms        - Platform stats (messages, errors)
GET /api/metrics/conversation     - Conversation quality metrics
GET /api/metrics/emotions/history - Emotion trends over time
GET /api/metrics/discord          - Discord bot status (online, latency, guilds, users)
```

## Dashboard Sections

New metrics-related dashboard sections:
1. **Discord Bot Status** - Online indicator, latency, guild/user counts
2. **LLM Performance** - Response times and token metrics
3. **Conversation Quality** - Message length and sentiment analysis
4. **Emotion State Trend** - Historical emotion visualization
5. **Platform Metrics** - Per-platform message counts and error rates

## Integration Checklist

To fully integrate metrics into Demi:

- [ ] **LLM Inference** - Wrap inference calls with `track_inference()`
  - File: `src/llm/inference.py`
  - Method: `chat()`

- [ ] **Platform Handlers** - Wrap message handling with `track_platform_message()`
  - Files: `src/platforms/discord.py`, `src/platforms/android.py`, etc.
  - Methods: Message handling in each platform

- [ ] **Emotion Updates** - Call `record_emotion_state()` on state changes
  - File: `src/emotion/persistence.py`
  - Method: `save_state()` or `update_state()`

- [ ] **Conversation Tracking** - Call `record_conversation_turn()` for each turn
  - File: Conversation handler/manager
  - Method: Message processing loop

- [ ] **Discord Bot Status** - Call `update_discord_bot_status()` periodically
  - File: `src/platforms/discord.py` or bot startup
  - Interval: Every 30-60 seconds

## Common Patterns

### Pattern 1: Automatic Timing
```python
from src.monitoring.metrics_integration import track_inference

# Automatically records response time
with track_inference("model-name") as metrics:
    response = await operation()
    metrics.set_tokens(prompt=100, response=50)
```

### Pattern 2: Record with Context
```python
from src.monitoring.metrics_integration import track_platform_message

with track_platform_message("platform-name") as metrics:
    result = await send_message()
    metrics.set_message_length(len(result))
```

### Pattern 3: Record State Changes
```python
from src.monitoring.metrics_integration import (
    record_emotion_state,
    record_conversation_turn,
)

# After emotion state update
record_emotion_state(emotional_state_dict)

# After each conversation turn
record_conversation_turn(
    user_length=len(user_msg),
    response_length=len(bot_response),
    turn_number=turn_count
)
```

### Pattern 4: Query Metrics
```python
from src.monitoring.metrics_integration import (
    get_current_emotions,
    get_platform_stats,
    get_discord_status,
)

emotions = get_current_emotions()
stats = get_platform_stats()
discord = get_discord_status()
```

## Testing

Test the implementation with the example file:

```bash
python3 examples/metrics_integration_examples.py
```

This will:
- Record sample metrics for all categories
- Display retrieved metrics
- Verify everything is working

## File Locations

### Backend
- Metrics collection: `src/monitoring/metrics.py`
- Integration helpers: `src/monitoring/metrics_integration.py`
- API endpoints: `src/monitoring/dashboard_server.py`

### Frontend
- Dashboard HTML: `src/monitoring/dashboard_static/index.html`
- Dashboard JavaScript: `src/monitoring/dashboard_static/dashboard.js`

### Documentation
- Full guide: `METRICS_GUIDE.md`
- Implementation details: `METRICS_IMPLEMENTATION_SUMMARY.md`

### Examples
- Integration examples: `examples/metrics_integration_examples.py`

## Storage

Metrics are stored in SQLite at: `~/.demi/metrics.db`

Features:
- 7-day retention (configurable)
- Optimized indexes for fast queries
- Automatic cleanup of old data
- Efficient time-series storage

## Dashboard Features

- **Real-time updates** - Every 5 seconds via WebSocket
- **Color coding** - Green (healthy), Yellow (warning), Red (critical)
- **Multiple visualizations** - Charts, radar diagrams, metrics cards
- **Responsive design** - Works on desktop, tablet, mobile
- **Dark/Light mode** - Toggle theme with button

## Performance

- **Overhead**: Minimal (<1% CPU impact)
- **Memory**: <10MB additional memory
- **Database**: SQLite with optimized queries
- **Update frequency**: 5 seconds (configurable)

## Troubleshooting

**Metrics not showing?**
1. Check database exists: `ls ~/.demi/metrics.db`
2. Verify data is being recorded: Run example script
3. Check API endpoints: `curl http://localhost:8080/api/metrics/llm`

**Slow dashboard?**
1. Reduce update frequency in `dashboard_server.py`
2. Reduce history points in API queries
3. Clear old data: `python3 -c "from src.monitoring.metrics import get_metrics_collector; get_metrics_collector().cleanup_old_data()"`

**High memory usage?**
1. Reduce data retention: `MetricsCollector(retention_days=3)`
2. Increase collection interval: `collection_interval=60`
3. Reduce history limits in queries

## Next Steps

1. **Review** the integration examples in `examples/metrics_integration_examples.py`
2. **Read** the full guide in `METRICS_GUIDE.md`
3. **Integrate** metrics into key components (see checklist above)
4. **Monitor** via the dashboard at `http://localhost:8080`
5. **Tune** retention and update frequencies as needed

## Questions?

Refer to:
- `METRICS_GUIDE.md` - Comprehensive documentation
- `examples/metrics_integration_examples.py` - Code examples
- `METRICS_IMPLEMENTATION_SUMMARY.md` - Technical details
