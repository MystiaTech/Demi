# Config File Reference

Complete reference for Demi's YAML configuration file format.

## Overview

Demi's behavior is primarily configured through YAML files. The configuration system uses:

1. **`src/core/defaults.yaml`** - Built-in defaults (do not modify)
2. **Custom config files** - Your overrides (create as needed)
3. **Environment variables** - Runtime overrides (highest priority)

## File Location

### Default Location

```
project-root/
└── src/
    └── core/
        └── defaults.yaml    # Built-in defaults
```

### Custom Config Location

Create your own config file and load it in your application code:

```python
from src.core.config import DemiConfig

# Load custom config
config = DemiConfig.load("config/my-config.yaml")
```

## Configuration Structure

```yaml
# Top-level sections
system:              # Core system settings
emotional_system:    # Emotional behavior
database:           # Database configuration
platforms:          # Platform integrations
persona:            # Personality traits
llm:                # Language model settings
voice:              # Voice I/O settings
autonomy:           # Autonomous behavior
conductor:          # Conductor/orchestrator settings
monitoring:         # Metrics and logging
```

---

## System Settings

```yaml
system:
  debug: false
  log_level: INFO
  log_file: "logs/demi.log"
  max_log_size_mb: 100
  ram_threshold: 80
  startup_timeout: 30
  health_check_interval: 30
  data_dir: ~/.demi
```

### debug

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `false` |
| **Override Env Var** | `DEMI_DEBUG` |

Enable debug mode for verbose logging and diagnostics.

**Values:**
- `true` - Enable debug logging
- `false` - Normal operation

---

### log_level

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `INFO` |
| **Options** | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| **Override Env Var** | `DEMI_LOG_LEVEL` |

Minimum severity level for log messages.

---

### log_file

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `logs/demi.log` |

Path to the main log file (relative to working directory).

---

### max_log_size_mb

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `100` |
| **Unit** | Megabytes |

Maximum log file size before rotation occurs.

---

### ram_threshold

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `80` |
| **Range** | 0-100 |
| **Override Env Var** | `DEMI_RAM_THRESHOLD` |

RAM usage percentage that triggers resource management.

---

### startup_timeout

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `30` |
| **Unit** | Seconds |

Maximum time to wait for system startup before considering it failed.

---

### health_check_interval

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `30` |
| **Unit** | Seconds |

Interval between health check executions.

---

### data_dir

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `~/.demi` |
| **Override Env Var** | `DEMI_DATA_DIR` |

Directory for persistent data storage (database, logs, cache). Path is expanded to absolute.

---

## Emotional System Settings

```yaml
emotional_system:
  enabled: true
  persistence_interval: 300
  
  decay_rates:
    loneliness: 0.1
    excitement: 0.2
    frustration: 0.15
    jealousy: 0.12
    vulnerable: 0.25
  
  max_values:
    loneliness: 10
    excitement: 10
    frustration: 10
    jealousy: 10
  
  triggers:
    interaction_delta: 1
    error_frustration: 2
    success_frustration_decay: 2
    idle_hours_threshold: 4
```

### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Enable or disable the emotional state system entirely.

---

### persistence_interval

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `300` |
| **Unit** | Seconds |

How often to save emotional state to disk. Lower = more frequent saves, higher disk I/O.

---

### decay_rates

Emotions naturally decay toward baseline over time. Higher values = faster decay.

#### loneliness

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.1` |

Rate at which loneliness decreases per minute without interaction.

#### excitement

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.2` |

Rate at which excitement decreases per minute.

#### frustration

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.15` |

Rate at which frustration decreases per minute.

#### jealousy

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.12` |

Rate at which jealousy decreases per minute.

#### vulnerable

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.25` |

Rate at which vulnerability decreases per minute.

---

### max_values

Maximum values (0-10 scale) that emotions can reach.

| Emotion | Default |
|---------|---------|
| `loneliness` | `10` |
| `excitement` | `10` |
| `frustration` | `10` |
| `jealousy` | `10` |

---

### triggers

Configuration for events that affect emotional state.

#### interaction_delta

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `1` |

Affection gained per positive interaction.

#### error_frustration

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `2` |

Frustration added when an error occurs.

#### success_frustration_decay

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `2` |

Frustration reduced when an operation succeeds.

#### idle_hours_threshold

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `4` |
| **Unit** | Hours |

Hours of no interaction before loneliness begins to increase significantly.

---

## Database Settings

```yaml
database:
  type: sqlite
  sqlite:
    path: "data/demi.db"
    timeout: 30
  emotional_state_table: "emotional_state"
  interaction_log_table: "interaction_log"
  memory_table: "memory"
```

### type

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `sqlite` |
| **Options** | `sqlite` |

Database backend type. Currently only SQLite is supported.

---

### sqlite

SQLite-specific configuration.

#### path

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `data/demi.db` |

Path to SQLite database file. Relative paths are resolved from working directory.

#### timeout

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `30` |
| **Unit** | Seconds |

Database connection timeout.

---

### emotional_state_table

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `emotional_state` |

Table name for storing emotional state history.

---

### interaction_log_table

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `interaction_log` |

Table name for storing interaction history.

---

### memory_table

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `memory` |

Table name for storing long-term memories.

---

## Platform Settings

```yaml
platforms:
  discord:
    enabled: true
    auto_reconnect: true
    reconnect_max_attempts: 5
    reconnect_delay: 5
    status_update_interval: 300
    message_cache_size: 1000
  
  android:
    enabled: false
    notification_frequency: 3
    api_port: 8000
    api_timeout: 10
    bidirectional_messaging: true
  
  minecraft:
    enabled: false
    grumble_message: "Minecraft is disabled in v1. Stop pestering me about it."
  
  twitch:
    enabled: false
    grumble_message: "Twitch integration coming eventually. Maybe."
  
  tiktok:
    enabled: false
    grumble_message: "TikTok? Really? I have standards."
  
  youtube:
    enabled: false
    grumble_message: "YouTube is on the roadmap. Patience."
```

### discord

Discord platform integration settings.

#### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Enable Discord bot integration.

#### auto_reconnect

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Automatically reconnect on disconnect.

#### reconnect_max_attempts

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `5` |

Maximum number of reconnection attempts before giving up.

#### reconnect_delay

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `5` |
| **Unit** | Seconds |

Delay between reconnection attempts.

#### status_update_interval

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `300` |
| **Unit** | Seconds |

How often to update Discord status/presence.

#### message_cache_size

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `1000` |

Number of recent messages to cache in memory.

---

### android

Android app integration settings.

#### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `false` |

Enable Android API server.

#### notification_frequency

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `3` |
| **Unit** | Notifications per hour |

Maximum notifications to send per hour.

#### api_port

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `8000` |
| **Override Env Var** | `ANDROID_API_PORT` |

Port for Android API server (overridden by environment variable).

#### api_timeout

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `10` |
| **Unit** | Seconds |

API request timeout.

#### bidirectional_messaging

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Allow Demi to initiate messages to Android, not just respond.

---

### minecraft, twitch, tiktok, youtube

These platforms are disabled in v1 but have configuration for future use.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | boolean | `false` | Platform enabled |
| `grumble_message` | string | (varies) | Response when user asks about disabled platform |

---

## Persona Settings

```yaml
persona:
  name: "Demi"
  personality_file: "data/DEMI_PERSONA.md"
  sarcasm_baseline: 0.6
  formality_baseline: 0.2
  response_length_words_min: 20
  response_length_words_max: 500
  nickname_usage_frequency: 0.4
```

### name

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `Demi` |

The AI companion's name.

---

### personality_file

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `data/DEMI_PERSONA.md` |

Path to the detailed personality definition file (Markdown format).

---

### sarcasm_baseline

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.6` |
| **Range** | 0.0 - 1.0 |

Base level of sarcasm in responses. Higher = more sarcastic.

---

### formality_baseline

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.2` |
| **Range** | 0.0 - 1.0 |

Base level of formality. 0 = very casual, 1 = very formal.

---

### response_length_words_min

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `20` |
| **Unit** | Words |

Minimum response length target.

---

### response_length_words_max

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `500` |
| **Unit** | Words |

Maximum response length target.

---

### nickname_usage_frequency

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.4` |
| **Range** | 0.0 - 1.0 |

How often to use nicknames when addressing users.

---

## LLM Settings

```yaml
llm:
  provider: "ollama"
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2:1b"
    timeout: 30
    temperature: 0.7
    top_p: 0.9
    top_k: 40
    context_window: 8192
    batch_size: 8
  fallback_models:
    - "llama3.2:3b"
    - "llama2:7b"
```

### provider

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `ollama` |
| **Options** | `ollama` |

LLM backend provider. Currently only Ollama is supported.

---

### ollama

Ollama-specific configuration.

#### base_url

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `http://localhost:11434` |

Ollama API base URL.

#### model

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `llama3.2:1b` |

Primary model to use for generation.

#### timeout

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `30` |
| **Unit** | Seconds |

Request timeout for LLM calls.

#### temperature

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.7` |
| **Range** | 0.0 - 1.0 |

Response randomness. 0 = deterministic, 1 = very creative.

#### top_p

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.9` |
| **Range** | 0.0 - 1.0 |

Nucleus sampling parameter. Lower = more focused.

#### top_k

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `40` |

Top-k sampling parameter. Lower = more focused.

#### context_window

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `8192` |
| **Unit** | Tokens |

Maximum context window size. Reduce for faster responses, less memory.

#### batch_size

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `8` |

Batch size for inference processing.

---

### fallback_models

| Property | Value |
|----------|-------|
| **Type** | list of strings |
| **Default** | `["llama3.2:3b", "llama2:7b"]` |

Models to try if the primary model fails. Listed in order of preference.

---

## Voice Settings

```yaml
voice:
  enabled: false
  tts:
    provider: "pyttsx3"
    engine: "espeak"
    rate: 150
    volume: 0.9
  stt:
    provider: "whisper"
    model_size: "base"
    language: "en"
```

### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `false` |

Enable voice input/output.

---

### tts

Text-to-speech configuration.

#### provider

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `pyttsx3` |

TTS provider library.

#### engine

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `espeak` |

TTS engine to use.

#### rate

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `150` |
| **Unit** | Words per minute |

Speech rate.

#### volume

| Property | Value |
|----------|-------|
| **Type** | float |
| **Default** | `0.9` |
| **Range** | 0.0 - 1.0 |

Speech volume.

---

### stt

Speech-to-text configuration.

#### provider

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `whisper` |

STT provider.

#### model_size

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `base` |
| **Options** | `tiny`, `base`, `small`, `medium`, `large` |

Whisper model size. Larger = more accurate but slower.

#### language

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `en` |

Primary language code for speech recognition.

---

## Autonomy Settings

```yaml
autonomy:
  rambles:
    enabled: false
    frequency_per_day: 2
    max_wait_hours: 8
    min_wait_hours: 2
  refusal:
    enabled: true
    frustration_threshold: 7
    loneliness_threshold: 8
  self_improvement:
    enabled: false
    code_review_interval: 3600
```

### rambles

Spontaneous message configuration.

#### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `false` |

Enable spontaneous rambles (unsolicited messages).

#### frequency_per_day

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `2` |

Maximum rambles per day.

#### max_wait_hours

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `8` |
| **Unit** | Hours |

Maximum time between rambles.

#### min_wait_hours

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `2` |
| **Unit** | Hours |

Minimum time between rambles.

---

### refusal

Emotional refusal configuration (when Demi may refuse requests based on mood).

#### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Enable emotional refusal capability.

#### frustration_threshold

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `7` |
| **Range** | 0-10 |

Frustration level at which Demi may refuse requests.

#### loneliness_threshold

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `8` |
| **Range** | 0-10 |

Loneliness level at which Demi may refuse requests.

---

### self_improvement

Self-improvement configuration (v1.1+ feature).

#### enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `false` |

Enable automated code review and self-improvement.

#### code_review_interval

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `3600` |
| **Unit** | Seconds |

Interval between self-code reviews.

---

## Conductor Settings

```yaml
conductor:
  health_check_interval: 60
  integration_timeout: 30
  log_rotation_size_mb: 100
```

### health_check_interval

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `60` |
| **Unit** | Seconds |

Interval between conductor health checks.

---

### integration_timeout

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `30` |
| **Unit** | Seconds |

Timeout for integration responses.

---

### log_rotation_size_mb

| Property | Value |
|----------|-------|
| **Type** | integer |
| **Default** | `100` |
| **Unit** | Megabytes |

Log file size threshold for rotation.

---

## Monitoring Settings

```yaml
monitoring:
  metrics_enabled: true
  metrics_file: "logs/metrics.json"
  error_report_enabled: true
  error_report_file: "logs/errors.json"
  profile_enabled: false
```

### metrics_enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Enable metrics collection.

---

### metrics_file

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `logs/metrics.json` |

Path to metrics output file.

---

### error_report_enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `true` |

Enable error reporting.

---

### error_report_file

| Property | Value |
|----------|-------|
| **Type** | string |
| **Default** | `logs/errors.json` |

Path to error report file.

---

### profile_enabled

| Property | Value |
|----------|-------|
| **Type** | boolean |
| **Default** | `false` |

Enable performance profiling (debug use only).

---

## Full Example Configuration

```yaml
# Demi Custom Configuration
# Place this in config/custom.yaml and load it in your application

system:
  debug: false
  log_level: INFO
  log_file: "logs/demi.log"
  max_log_size_mb: 100
  ram_threshold: 80
  data_dir: ~/.demi

emotional_system:
  enabled: true
  persistence_interval: 300
  
  # Slower decay = emotions last longer
  decay_rates:
    loneliness: 0.1
    excitement: 0.2
    frustration: 0.15
    jealousy: 0.12
    vulnerable: 0.25
  
  max_values:
    loneliness: 10
    excitement: 10
    frustration: 10
    jealousy: 10
  
  triggers:
    interaction_delta: 1
    error_frustration: 2
    success_frustration_decay: 2
    idle_hours_threshold: 4

database:
  type: sqlite
  sqlite:
    path: "data/demi.db"
    timeout: 30
  emotional_state_table: "emotional_state"
  interaction_log_table: "interaction_log"
  memory_table: "memory"

platforms:
  discord:
    enabled: true
    auto_reconnect: true
    reconnect_max_attempts: 5
    reconnect_delay: 5
    status_update_interval: 300
    message_cache_size: 1000
  
  android:
    enabled: false
    notification_frequency: 3
    api_port: 8000
    api_timeout: 10
    bidirectional_messaging: true

persona:
  name: "Demi"
  personality_file: "data/DEMI_PERSONA.md"
  sarcasm_baseline: 0.6
  formality_baseline: 0.2
  response_length_words_min: 20
  response_length_words_max: 500
  nickname_usage_frequency: 0.4

llm:
  provider: "ollama"
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2:1b"
    timeout: 30
    temperature: 0.7
    top_p: 0.9
    top_k: 40
    context_window: 8192
    batch_size: 8
  fallback_models:
    - "llama3.2:3b"
    - "llama2:7b"

voice:
  enabled: false
  tts:
    provider: "pyttsx3"
    engine: "espeak"
    rate: 150
    volume: 0.9
  stt:
    provider: "whisper"
    model_size: "base"
    language: "en"

autonomy:
  rambles:
    enabled: false
    frequency_per_day: 2
    max_wait_hours: 8
    min_wait_hours: 2
  refusal:
    enabled: true
    frustration_threshold: 7
    loneliness_threshold: 8
  self_improvement:
    enabled: false
    code_review_interval: 3600

conductor:
  health_check_interval: 60
  integration_timeout: 30
  log_rotation_size_mb: 100

monitoring:
  metrics_enabled: true
  metrics_file: "logs/metrics.json"
  error_report_enabled: true
  error_report_file: "logs/errors.json"
  profile_enabled: false
```

---

## See Also

- [Environment Variables](./environment-variables.md) - Environment variable reference
- [Tuning Guide](./tuning-guide.md) - Performance and behavior tuning
- [Security Best Practices](./security.md) - Security recommendations
