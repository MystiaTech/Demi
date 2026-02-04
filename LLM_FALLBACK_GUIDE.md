# LLM Provider Fallback Guide

## Overview

DEMI now supports automatic fallback from Ollama to LMStudio, ensuring uninterrupted service even if your primary LLM provider becomes unavailable.

## How It Works

The unified LLM inference system (`UnifiedLLMInference`) attempts to connect in the following order:

1. **Primary**: Ollama (default provider)
2. **Fallback**: LMStudio (if Ollama is unavailable and fallback is enabled)

### Automatic Fallback

When DEMI encounters an error or unavailability from Ollama:
- It logs the issue
- It immediately attempts to use LMStudio
- It continues seamlessly with the fallback provider
- When Ollama becomes available again, it automatically switches back

### Health Checks

Both providers are health-checked:
- Every 60 seconds (cached between checks)
- Before each message when fallback has occurred
- Independently of message traffic

## Setup

### 1. Install Dependencies

```bash
pip install aiohttp>=3.8.0
```

### 2. Configure Environment Variables

#### For Ollama (Primary)
```bash
# In .env
OLLAMA_BASE_URL=http://localhost:11434
```

#### For LMStudio (Fallback)
```bash
# In .env
LMSTUDIO_BASE_URL=http://localhost:1234
DEMI_ENABLE_LLM_FALLBACK=true
```

### 3. Start Your LLM Server(s)

#### Option A: Only Ollama (Fallback Disabled)
```bash
# Terminal 1 - Start Ollama
ollama serve

# Terminal 2 - Start DEMI
python -m src.conductor
```

#### Option B: Ollama + LMStudio (Recommended)
```bash
# Terminal 1 - Start Ollama
ollama serve

# Terminal 2 - Start LMStudio
# (LMStudio typically has a GUI launch, or run server directly)

# Terminal 3 - Start DEMI
python -m src.conductor
```

#### Option C: Only LMStudio (Ollama Optional)
```bash
# Terminal 1 - Start LMStudio
# (LMStudio typically has a GUI launch, or run server directly)

# Terminal 2 - Start DEMI
python -m src.conductor
# Ollama will fail health check, automatically fall back to LMStudio
```

## Configuration

### defaults.yaml

```yaml
llm:
  provider: "ollama"
  enable_fallback: true  # Enable automatic fallback to LMStudio
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.2:1b"
    timeout: 30
    temperature: 0.7
    context_window: 8192
  lmstudio:
    base_url: "http://localhost:1234"
    timeout: 30
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server endpoint |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234` | LMStudio server endpoint |
| `DEMI_ENABLE_LLM_FALLBACK` | `true` | Enable fallback mechanism |

### Disable Fallback (If Needed)

To disable automatic fallback and use Ollama only:

```bash
export DEMI_ENABLE_LLM_FALLBACK=false
python -m src.conductor
```

## Logging

The fallback system logs important events:

```
[INFO] Using Ollama provider
[INFO] Ollama unavailable, switched to LMStudio provider
[DEBUG] Using Ollama provider
[WARNING] Ollama inference failed: Connection refused
[INFO] Switched to LMStudio provider
```

## Architecture

### UnifiedLLMInference Class

Coordinates between providers:
- Maintains references to both Ollama and LMStudio clients
- Tracks active provider state
- Performs intelligent health checks
- Routes requests to available provider
- Handles graceful degradation

### OllamaInference Class

Primary provider:
- Uses `ollama` Python package
- Async interface for non-blocking calls
- Context trimming and token management
- Full error handling

### LMStudioInference Class

Fallback provider:
- Uses `aiohttp` for API calls
- Compatible with OpenAI API format
- Same async interface as Ollama
- Identical token management logic

## Use Cases

### Development

Keep both services running for testing:
```bash
# Terminal 1
ollama serve

# Terminal 2
lmstudio  # or LMStudio GUI

# Terminal 3
python -m src.conductor
# Both providers are available for testing
```

### Production

Run only what you need:
```bash
# Main server - Ollama
ollama serve

# DEMI auto-switches to LMStudio if Ollama fails
python -m src.conductor
```

### High Availability

Run redundant providers:
```bash
# Server 1
ollama serve

# Server 2 (or local fallback)
lmstudio

# DEMI uses Ollama when available, seamlessly switches to LMStudio on failure
python -m src.conductor
```

## Troubleshooting

### "Both Ollama and LMStudio providers failed"

This means:
1. Neither provider is running
2. Both are misconfigured
3. Both have connectivity issues

**Solutions:**
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Verify LMStudio is running: `curl http://localhost:1234/v1/models`
- Check `OLLAMA_BASE_URL` and `LMSTUDIO_BASE_URL` environment variables
- Verify firewall isn't blocking connections

### "Ollama provider failed and fallback is disabled"

This means:
- Ollama failed to respond
- Fallback is disabled (`DEMI_ENABLE_LLM_FALLBACK=false`)

**Solutions:**
- Enable fallback: `export DEMI_ENABLE_LLM_FALLBACK=true`
- Or fix Ollama connectivity
- Check Ollama logs for errors

### Provider Switching Too Often

If logs show frequent provider switches:
- Check network stability
- Verify provider health manually: `curl http://localhost:11434/api/tags`
- Increase health check timeout in config
- Check provider logs for performance issues

### Slow Responses

If responses are slower after fallback:
1. LMStudio may be slower than Ollama for your use case
2. Both providers may be struggling
3. Network latency may be high

**Solutions:**
- Profile response times for each provider
- Ensure adequate hardware resources
- Consider dedicated server for each provider
- Optimize model selection for each provider

## Advanced: Custom Health Check Interval

To modify how often health checks occur, edit `src/llm/inference.py`:

```python
# In UnifiedLLMInference.__init__
self._health_check_interval = 30  # Change from 60 to 30 seconds
```

Lower values = faster switching but more overhead
Higher values = less overhead but slower fallback activation

## Advanced: Manual Provider Selection

Currently, provider selection is automatic. To implement manual selection:

```python
# Future enhancement - not yet implemented
llm = UnifiedLLMInference(config, logger)
llm.force_provider("lmstudio")  # Force use of LMStudio
response = await llm.chat(messages)
```

## Performance Comparison

### Ollama
- **Pros**: Local installation, fast for small models, no external dependencies
- **Cons**: Requires proper GPU/CPU setup, limited model variety

### LMStudio
- **Pros**: User-friendly interface, wide model selection, good performance
- **Cons**: May require more resources, different model loading mechanism

## Model Compatibility

Both providers support the same model format via OpenAI-compatible APIs:

```python
# Both can use the same model specification
messages = [{"role": "user", "content": "Hello"}]
response = await llm.chat(messages)
# Works with either provider
```

## Future Enhancements

Potential improvements:
1. **Round-robin** load balancing between providers
2. **Geographic** provider selection
3. **Performance** metrics collection
4. **Automatic** provider quality scoring
5. **Canary** deployment patterns
6. **Provider affinity** based on workload type

## Support

For issues with fallback functionality:
1. Check provider connectivity: `curl http://localhost:<port>/api/tags`
2. Review logs for specific error messages
3. Verify environment variables are set correctly
4. Test each provider independently
5. Check network connectivity and firewalls

## See Also

- [Ollama Documentation](https://ollama.ai)
- [LMStudio Documentation](https://lmstudio.ai)
- [DEMI Configuration Guide](src/core/defaults.yaml)
- [Conductor Documentation](src/conductor/README.md)
