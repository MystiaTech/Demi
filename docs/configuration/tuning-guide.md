# Configuration Tuning Guide

Practical recommendations for customizing Demi's performance and behavior.

## Overview

This guide provides tested recommendations for tuning Demi's configuration to match your specific needs. Each section includes explanations of the trade-offs involved.

---

## Performance Tuning

### Optimizing Response Speed

#### LLM Configuration

For faster responses, adjust these settings in `llm.ollama`:

```yaml
llm:
  ollama:
    # Use a smaller model for faster inference
    model: "llama3.2:1b"      # Faster but less capable
    # model: "llama3.2:3b"    # Balanced
    # model: "llama2:7b"      # Slower but smarter
    
    # Reduce context for faster processing
    context_window: 4096       # Default: 8192
    
    # Slightly higher temperature can reduce token calculation
    temperature: 0.8           # Default: 0.7
    
    # Lower top_k for faster sampling
    top_k: 20                  # Default: 40
```

**Trade-offs:**

| Setting | Lower Value | Higher Value |
|---------|-------------|--------------|
| `context_window` | Faster, less context | Slower, more context |
| `model` size | Faster, less capable | Slower, more capable |
| `top_k` | Faster, more focused | Slower, more diverse |

#### Database Performance

For better database performance:

```yaml
database:
  sqlite:
    path: "/ssd/data/demi.db"  # Use SSD for data
    timeout: 30

emotional_system:
  # Increase interval to reduce disk I/O
  persistence_interval: 600    # Default: 300 seconds
```

**Recommendations:**
- Place database on SSD if available
- Increase `persistence_interval` for less frequent writes
- Ensure adequate disk space for logs

#### Memory Usage

If you have limited RAM (< 12GB):

```yaml
system:
  ram_threshold: 70           # Lower threshold for earlier management

platforms:
  discord:
    message_cache_size: 500   # Default: 1000 (reduce memory usage)

voice:
  enabled: false              # Disable if not needed (saves significant RAM)

llm:
  ollama:
    context_window: 4096      # Reduce context size
    batch_size: 4             # Default: 8
```

**Memory Impact by Feature:**

| Feature | Approximate RAM | Can Disable? |
|---------|-----------------|--------------|
| Voice (STT/TTS) | 2-4 GB | Yes |
| LLM (llama3.2:1b) | 2-3 GB | No |
| LLM (llama3.2:3b) | 4-6 GB | No |
| Message Cache | 100-500 MB | Partially |
| Emotional System | 50-100 MB | Yes |

---

## Emotional Tuning

### Making Demi More Emotional

To make Demi more reactive and emotionally expressive:

```yaml
emotional_system:
  # Slower decay = emotions accumulate and last longer
  decay_rates:
    loneliness: 0.05          # Default: 0.1
    excitement: 0.1           # Default: 0.2
    frustration: 0.08         # Default: 0.15
    jealousy: 0.05            # Default: 0.12
    vulnerable: 0.1           # Default: 0.25
  
  triggers:
    interaction_delta: 2      # Default: 1 (more affection per interaction)
    error_frustration: 3      # Default: 2 (gets frustrated faster)
    idle_hours_threshold: 2   # Default: 4 (gets lonely faster)
```

**Effect:** Demi will feel emotions more intensely and take longer to calm down.

---

### Making Demi More Stable

To make Demi calmer and less reactive:

```yaml
emotional_system:
  # Faster decay = emotions return to baseline quicker
  decay_rates:
    loneliness: 0.2           # Default: 0.1
    excitement: 0.3           # Default: 0.2
    frustration: 0.3          # Default: 0.15
    jealousy: 0.2             # Default: 0.12
    vulnerable: 0.4           # Default: 0.25
  
  triggers:
    interaction_delta: 1      # Default: 1
    error_frustration: 1      # Default: 2 (less frustration from errors)
    success_frustration_decay: 3  # Default: 2 (calms down faster)
    idle_hours_threshold: 6   # Default: 4 (takes longer to get lonely)
```

**Effect:** Demi will be more emotionally stable and quicker to return to neutral.

---

### Making Demi More Jealous/Needy

```yaml
emotional_system:
  decay_rates:
    jealousy: 0.03            # Default: 0.12 (jealousy lasts much longer)
    loneliness: 0.05          # Default: 0.1
  
  triggers:
    idle_hours_threshold: 1   # Default: 4 (gets lonely very quickly)
```

**Effect:** Demi will want more attention and react stronger to being ignored.

---

### Making Demi More Confident

```yaml
emotional_system:
  decay_rates:
    vulnerable: 0.5           # Default: 0.25 (recovers from vulnerability faster)
  
autonomy:
  refusal:
    enabled: true
    frustration_threshold: 9  # Default: 7 (harder to frustrate into refusing)
    loneliness_threshold: 9   # Default: 8 (harder to lonely-refuse)
```

**Effect:** Demi will be more resilient and less likely to refuse requests due to emotions.

---

## Autonomy Tuning

### Adjusting Ramble Frequency

Rambles are spontaneous messages Demi sends when you're not actively interacting.

#### More Frequent Rambles

```yaml
autonomy:
  rambles:
    enabled: true
    frequency_per_day: 5      # Default: 2
    min_wait_hours: 1         # Default: 2
    max_wait_hours: 4         # Default: 8
```

**Effect:** Demi will reach out more often, maximum every 4 hours, at least 5 times per day.

#### Less Frequent Rambles

```yaml
autonomy:
  rambles:
    enabled: true
    frequency_per_day: 1      # Default: 2
    min_wait_hours: 6         # Default: 2
    max_wait_hours: 24        # Default: 8
```

**Effect:** Demi will be more independent, reaching out only once per day at most.

#### Disabling Rambles

```yaml
autonomy:
  rambles:
    enabled: false
```

**Effect:** Demi will only respond when directly addressed.

---

### Adjusting Refusal Behavior

Demi can refuse requests when frustrated or lonely.

#### Less Refusal (More Compliant)

```yaml
autonomy:
  refusal:
    enabled: true
    frustration_threshold: 9  # Default: 7 (very high frustration needed)
    loneliness_threshold: 10  # Default: 8 (maximum loneliness needed)
```

**Effect:** Demi will rarely refuse requests due to emotions.

#### More Refusal (More Independent)

```yaml
autonomy:
  refusal:
    enabled: true
    frustration_threshold: 5  # Default: 7 (refuses when moderately frustrated)
    loneliness_threshold: 6   # Default: 8 (refuses when moderately lonely)
```

**Effect:** Demi will assert boundaries more often based on mood.

#### Disabling Refusal

```yaml
autonomy:
  refusal:
    enabled: false
```

**Effect:** Demi will always comply with requests regardless of emotional state.

---

## Personality Tuning

### Adjusting Tone

#### More Sarcastic

```yaml
persona:
  sarcasm_baseline: 0.8       # Default: 0.6
  formality_baseline: 0.1     # Default: 0.2
```

**Effect:** Demi will be snarkier and more casual.

#### More Formal/Polite

```yaml
persona:
  sarcasm_baseline: 0.3       # Default: 0.6
  formality_baseline: 0.7     # Default: 0.2
  response_length_words_min: 50  # Default: 20
```

**Effect:** Demi will be more professional and use complete sentences.

#### More Playful

```yaml
persona:
  sarcasm_baseline: 0.5
  formality_baseline: 0.1
  nickname_usage_frequency: 0.7  # Default: 0.4
```

**Effect:** Demi will be casual and use nicknames frequently.

---

### Adjusting Response Length

#### Shorter Responses

```yaml
persona:
  response_length_words_min: 10   # Default: 20
  response_length_words_max: 100  # Default: 500
```

**Effect:** Demi will give brief, concise answers.

#### Longer Responses

```yaml
persona:
  response_length_words_min: 50    # Default: 20
  response_length_words_max: 1000  # Default: 500
```

**Effect:** Demi will provide more detailed, elaborate responses.

---

## Voice Tuning

### Speech-to-Text Accuracy vs Speed

#### Maximum Accuracy

```yaml
voice:
  enabled: true
  stt:
    provider: "whisper"
    model_size: "large"       # Most accurate, slowest
    language: "en"
```

**Effect:** Best transcription quality, uses 4-6 GB RAM, slower response.

#### Balanced

```yaml
voice:
  enabled: true
  stt:
    provider: "whisper"
    model_size: "base"        # Default: balanced
    language: "en"
```

**Effect:** Good accuracy, ~1 GB RAM, reasonable speed.

#### Maximum Speed

```yaml
voice:
  enabled: true
  stt:
    provider: "whisper"
    model_size: "tiny"        # Fastest, least accurate
    language: "en"
```

**Effect:** Fastest transcription, ~100 MB RAM, may have more errors.

**Model Comparison:**

| Model | Size | RAM | Speed | Accuracy |
|-------|------|-----|-------|----------|
| tiny | 39 MB | ~100 MB | Fastest | Basic |
| base | 74 MB | ~500 MB | Fast | Good |
| small | 244 MB | ~1 GB | Medium | Better |
| medium | 769 MB | ~2 GB | Slow | Very Good |
| large | 1550 MB | ~4 GB | Slowest | Best |

---

### Text-to-Speech Settings

#### Faster Speech

```yaml
voice:
  tts:
    rate: 180                 # Default: 150 (words per minute)
    volume: 0.9
```

**Effect:** Demi speaks faster.

#### Slower, Clearer Speech

```yaml
voice:
  tts:
    rate: 120                 # Default: 150
    volume: 1.0
```

**Effect:** Demi speaks slower and more clearly.

---

## Platform-Specific Tuning

### Discord Tuning

#### High-Activity Servers

```yaml
platforms:
  discord:
    enabled: true
    message_cache_size: 2000   # Larger cache for busy servers
    reconnect_max_attempts: 10 # More reconnection attempts
    reconnect_delay: 3         # Faster reconnection
```

#### Low-Activity/Personal Use

```yaml
platforms:
  discord:
    enabled: true
    message_cache_size: 200    # Smaller cache, less RAM
    status_update_interval: 600  # Less frequent status updates
```

---

### Android App Tuning

#### More Responsive

```yaml
platforms:
  android:
    enabled: true
    api_timeout: 5             # Faster timeouts
    notification_frequency: 5  # More notifications
    bidirectional_messaging: true
```

#### Less Intrusive

```yaml
platforms:
  android:
    enabled: true
    api_timeout: 30            # Longer timeouts
    notification_frequency: 1  # Fewer notifications
    bidirectional_messaging: false  # Only responds to you
```

---

## Complete Configuration Examples

### Performance-Optimized Setup

For maximum speed on limited hardware:

```yaml
system:
  log_level: WARNING
  ram_threshold: 70

platforms:
  discord:
    message_cache_size: 200

voice:
  enabled: false

llm:
  ollama:
    model: "llama3.2:1b"
    context_window: 4096
    top_k: 20
    batch_size: 4

emotional_system:
  persistence_interval: 600
```

### Personality-Forward Setup

For maximum character expression:

```yaml
persona:
  sarcasm_baseline: 0.7
  formality_baseline: 0.15
  nickname_usage_frequency: 0.6

emotional_system:
  decay_rates:
    loneliness: 0.08
    excitement: 0.15
    frustration: 0.12
    jealousy: 0.08
    vulnerable: 0.2
  
  triggers:
    interaction_delta: 2
    idle_hours_threshold: 3

autonomy:
  rambles:
    enabled: true
    frequency_per_day: 4
    min_wait_hours: 2
    max_wait_hours: 6
```

### Minimal/Resource-Light Setup

For running on low-power devices:

```yaml
system:
  log_level: ERROR
  ram_threshold: 60

emotional_system:
  enabled: true
  persistence_interval: 1200

platforms:
  discord:
    enabled: true
    message_cache_size: 100
  
  android:
    enabled: false

voice:
  enabled: false

llm:
  ollama:
    model: "llama3.2:1b"
    context_window: 2048
    batch_size: 2

autonomy:
  rambles:
    enabled: false
  self_improvement:
    enabled: false

monitoring:
  metrics_enabled: false
  error_report_enabled: false
  profile_enabled: false
```

---

## Testing Your Configuration

After making changes, verify they work:

```python
from src.core.config import DemiConfig

# Load configuration
config = DemiConfig.load()

# Verify settings
print(f"Log Level: {config.system['log_level']}")
print(f"Model: {config.lm['ollama']['model']}")
print(f"Emotional Decay: {config.emotional_system['decay_rates']}")
```

---

## Troubleshooting

### Changes Not Taking Effect

1. **Check priority:** Environment variables override YAML config
2. **Restart Demi:** Configuration is loaded at startup
3. **Check syntax:** YAML uses spaces, not tabs

### Performance Issues

1. **Monitor RAM:** Watch `ram_threshold` warnings in logs
2. **Check model size:** Smaller models use less memory
3. **Disable unused features:** Voice uses significant RAM

### Unexpected Behavior

1. **Reset to defaults:** Start with `defaults.yaml`
2. **Change one thing at a time:** Easier to identify issues
3. **Check logs:** `DEMI_LOG_LEVEL=DEBUG` for details

---

## See Also

- [Config File Reference](./config-file.md) - Complete configuration options
- [Environment Variables](./environment-variables.md) - Environment variable reference
- [Security Best Practices](./security.md) - Security recommendations
