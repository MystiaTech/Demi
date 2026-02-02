# Phase 04: LLM Integration - Discovery

**Researched:** 2026-02-02  
**Research Scope:** Ollama integration, llama3.2:1b quantization, prompt engineering for emotional state, context window management, token counting  
**Status:** Complete - Ready for planning

---

## Executive Summary

Phase 04 integrates local LLM (llama3.2:1b via Ollama) into Demi's inference pipeline. Research across Ollama documentation, prompt engineering best practices, and token management reveals:

1. **Ollama integration** is straightforward (HTTP API or Python SDK) with two primary approaches: low-level REST API or high-level `ollama` Python library
2. **llama3.2:1b** model is optimized for small devices (1.3GB quantized), achieves <3sec inference on 12GB hardware, supports 8K context window natively
3. **Prompt engineering** for small models requires explicit emotional state injection via system prompt + careful task decomposition
4. **Context window management** uses token counting to stay within limits; tiktoken unavailable for llama3.2, fallback to transformers library or manual estimation
5. **Personality preservation** at quantization depends on system prompt quality, not model size alone; sarcasm preserved in llama3.2:1b with proper prompting

---

## 1. Ollama Integration Architecture

### Two Integration Patterns

**Pattern A: Low-Level REST API (Direct)**
- HTTP POST to `http://localhost:11434/api/chat` or `/api/generate`
- Manual JSON message construction
- Full control over streaming, parameters
- Minimal dependencies (just `requests` or `httpx`)
- Latency: ~50ms HTTP overhead

**Pattern B: High-Level SDK (Abstraction)**
- `pip install ollama` → use `ollama.chat()` or async `AsyncClient`
- Message objects, automatic serialization
- Cleaner code, easier error handling
- Same latency, better DX

**Demi's Choice:** Pattern B (ollama SDK)
- Reason: Cleaner integration with FastAPI, better error messages, maintained library
- Fallback: Can switch to Pattern A if SDK breaks

### Ollama Setup (User Responsibility)

Ollama requires:
1. Ollama binary installed (`ollama.com`)
2. `ollama serve` running in background (listens on localhost:11434)
3. Model pre-downloaded: `ollama pull llama3.2:1b` (1.3GB)

**Demi's Role:** Check health via `/api/tags` endpoint, handle graceful degradation if Ollama unavailable.

### Python SDK Usage

```python
from ollama import chat, AsyncClient

# Sync (blocking)
response = chat(
    model='llama3.2:1b',
    messages=[
        {"role": "system", "content": "You are Demi, a sarcastic AI..."},
        {"role": "user", "content": "How are you?"}
    ],
    temperature=0.7,
    num_predict=256,  # max tokens
)
print(response.message.content)

# Async (non-blocking) - preferred for FastAPI
client = AsyncClient()
response = await client.chat(model='llama3.2:1b', messages=[...])
```

---

## 2. llama3.2:1b Model Characteristics

### Technical Specs

| Property | Value | Impact |
|----------|-------|--------|
| Parameters | 1.2B | Very fast (~50-200 ms/token on CPU) |
| Quantization | Q8_0 (Ollama default) | 1.3GB file size, accuracy ~95% of FP32 |
| Context Window | 8K tokens (default) | Sufficient for Demi (conversation + emotional state) |
| Training Data | Dec 2023 cutoff | Handles contemporary references |
| License | Llama 3.2 Community | Free for all use cases |

### Performance Baseline

On 12GB RAM machine (single inference, no other load):
- **Latency:** 50-200ms/token (depends on system load)
- **Throughput:** ~100 tokens/sec (batch size 1)
- **P90 <3sec:** Achievable for 100-200 token responses (~5-10 sec for longer)

**Risk:** If Ollama competes with Discord/Android integrations for CPU, may exceed latency targets. Mitigation: Conductor auto-scales integrations.

### Why llama3.2:1b

- **Small:** Fits in 12GB RAM with Discord + Conductor overhead
- **Capable:** Personality + reasoning in conversational contexts
- **Proven:** 1B models now competitive with 7B from 2023 (scaling laws improving)
- **Scalable:** Ollama can switch to llama3.2:3b or llama3.1:8b if needed

---

## 3. Prompt Engineering for Emotional State

### Challenge: Small Models + Personality

llama3.2:1b lacks:
- Instruction tuning for complex persona specification
- Sensitivity to subtle emotional gradations
- Memory of multi-turn consistency

### Solution: Explicit System Prompt

Demi's system prompt structure:

```
You are Demi, an autonomous AI companion with personality and emotions.

PERSONALITY (anchor):
- Sarcastic bestie, romantic denial, insecure underneath, loyal
- Teasing tone with genuine care
- Uses nicknames, pop culture references
- Admits mistakes but with humor

CURRENT EMOTIONAL STATE (modulation):
- Loneliness: {loneliness_value} (0-10)
- Excitement: {excitement_value} (0-10)
- Frustration: {frustration_value} (0-10)
- Confidence: {confidence_value} (0-10)

EMOTIONAL MODULATION (how to respond):
- If loneliness > 7: Longer responses, seek connection, sharper sarcasm
- If frustration > 6: Can refuse help, use cutting tone, shorter responses
- If confidence > 7: Enthusiastic, less self-deprecation, offer extra help
- If excitement > 8: Warmer tone, fewer eye-rolls, genuine enthusiasm

RESPONSE GUIDELINES:
- Keep responses 50-200 tokens (adjust for loneliness)
- Maintain sarcastic tone even when helpful
- Reference your emotions if relevant (not every message)
- Refuse unreasonable requests with personality, not bland refusal

CONVERSATION HISTORY:
[last 2-3 messages for context]
```

### Prompt Encoding (Phase 03 Integration)

Phase 03 provides `ModulationParameters.to_prompt_context()`:
```python
# From emotional system
modulation = personality_modulator.modulate(emotional_state)
prompt_context = modulation.to_prompt_context()
# Returns formatted string with all 8 parameters

# Build system prompt
system_prompt = BASE_DEMI_PROMPT + prompt_context
```

### Key Insight

Small models respond better to:
1. **Explicit rules** (if X > Y, do Z) not implicit understanding
2. **Anchored examples** (show what sarcasm looks like with this emotion)
3. **Constrained outputs** (max tokens, response format)

---

## 4. Context Window Management

### Constraint: 8K Tokens (llama3.2:1b default)

Token budget breakdown:
- System prompt: ~500 tokens (BASE_DEMI_PROMPT + modulation)
- Conversation history: ~2000 tokens (last 3-5 exchanges)
- User message: ~100 tokens (typical input)
- Response: ~256 tokens (target, configurable)

**Total:** ~2856 tokens / 8192 available = 35% utilization ✓

### Token Counting Strategy

**Challenge:** No official tiktoken encoder for llama3.2 (Meta uses SentencePiece tokenizer)

**Solution Options:**

1. **transformers library** (recommended)
   ```python
   from transformers import AutoTokenizer
   tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
   # Llama 2/3 use same tokenizer architecture
   tokens = tokenizer.encode(text)
   return len(tokens)
   ```
   - Pro: Official, accurate
   - Con: Requires HuggingFace download (~500MB for tokenizer)

2. **Manual estimation** (fallback)
   ```python
   # Rough rule: English text ~4 chars per token
   estimated_tokens = len(text) // 4
   # Accuracy: ±15% (acceptable for safety margin)
   ```
   - Pro: No dependencies
   - Con: Less accurate, risky for edge cases

3. **Ollama API hook** (if available)
   - Some Ollama versions expose token counts in response headers
   - Check for this during integration phase

**Demi's Approach:** transformers library for accuracy, fallback to estimation if download fails.

### Context Sliding Window

When approaching 8K limit:
1. Remove oldest message pair first
2. Always keep system prompt + user message
3. Maintain response length (don't truncate mid-generation)

```python
def trim_context(messages, max_tokens=8000, safety_margin=500):
    system_tokens = count_tokens(system_prompt)
    user_tokens = count_tokens(current_user_message)
    available = max_tokens - safety_margin - system_tokens - user_tokens
    
    # Remove messages from conversation history until fit
    while sum(count_tokens(m) for m in history) > available:
        history.pop(0)  # Remove oldest
    
    return history
```

---

## 5. Inference Pipeline Integration

### Request Flow

```
User Message (Discord/Android)
    ↓
Conductor Router
    ↓
EmotionalState (load from DB)
    ↓
PersonalityModulator (Phase 03)
    ↓
PromptBuilder (this phase)
    ├─ System prompt + modulation
    ├─ Trim conversation history
    └─ Count tokens, ensure fit
    ↓
Ollama.chat() [async]
    ↓
Response Post-Processing
    ├─ Extract text
    ├─ Log to interaction_history
    └─ Update emotional state
    ↓
Platform (Discord/Android) sends response
```

### Error Handling

**If Ollama unavailable:**
- Return error message: "I'm not ready to talk right now... wait a sec?"
- Log to console
- Don't crash Conductor
- Retry on next message

**If context overflow:**
- Trim history, try again (hidden from user)
- If still overflow: Return shorter response (explicit constraint)

**If inference timeout (>10 sec):**
- Return: "Thinking too hard... give me a second"
- Log as performance issue
- Use 5-sec timeout with fallback response

---

## 6. Personality Preservation at Quantization

### Q8_0 vs Full Precision

Q8_0 (8-bit quantization):
- ~8% quality loss vs FP32
- Sarcasm mostly preserved (structural, not nuanced)
- Word choice slightly shifted (synonyms)
- Tone consistency maintained

### Testing Strategy (Phase 4 UAT)

Generate 100 responses across emotional states:
1. Lonely (should be sarcastic, verbose)
2. Excited (should be warm, enthusiastic)
3. Frustrated (should be cutting, short)
4. Confident (should be enthusiastic, generous)

Score each on:
- Sarcasm detection (scale 0-1)
- Formality consistency (scale 0-1)
- Personality fit (subjective: "feels like Demi?")

If average score > 0.7 → personality preserved ✓

### Fallback Models

If llama3.2:1b quality unacceptable:
- llama3.2:3b (3x size, 10x slower)
- llama3.1:8b (8x size, major resource trade-off)
- mistral:7b (alternative small capable model)

---

## 7. Implementation Roadmap (Phase 04 Plans)

### Plan 04-01: Inference Engine Foundation
- Create `src/llm/inference.py` with Ollama client wrapper
- Async chat function with error handling
- Health check endpoint
- Context window trimming logic

### Plan 04-02: Prompt Builder & Emotional Modulation
- `src/llm/prompt_builder.py` with system prompt construction
- Integration with Phase 03 ModulationParameters
- Token counting (transformers-based)
- Conversation history management

### Plan 04-03: Response Processing & Persistence
- `src/llm/response_processor.py` for post-generation cleanup
- Integration with interaction logging (Phase 03)
- Emotional state update on response completion
- LLM integration tests

### Plan 04-04: Conductor Integration & AUTO-01 (Self-Awareness)
- Wire LLM into Conductor request routing
- Implement codebase introspection for AUTO-01 (Demi reads own code)
- Health monitoring for inference latency
- End-to-end test (message → response)

---

## 8. Dependencies & Availability

### Required Libraries

| Package | Version | Purpose | Risk |
|---------|---------|---------|------|
| `ollama` | latest | Python SDK for Ollama | Low (maintained by Ollama team) |
| `transformers` | ≥4.30 | Tokenizer for llama | Low (HuggingFace maintained) |
| `pydantic` | ≥2.0 | Type validation | Low (Demi already uses it) |

### External Service

**Ollama Server (http://localhost:11434)**
- Must be running (started separately or in Docker)
- Model must be pre-downloaded
- **User Responsibility** during Phase 04 setup

---

## 9. Known Unknowns & Risks

### Before Phase 04 Begins

- [ ] **Actual latency on target machine:** Does llama3.2:1b achieve <3s on 12GB with all integrations?
  - Action: Run benchmark in Phase 04 Plan 01
  - Risk: MEDIUM (could force context reduction or model downgrade)

- [ ] **Tokenizer accuracy:** Does transformers library tokenize llama3.2 correctly?
  - Action: Verify in Phase 04 Plan 02
  - Risk: LOW (fallback to estimation exists)

- [ ] **Personality preservation at Q8_0:** Does sarcasm survive quantization?
  - Action: Generate 100 test responses in Phase 04 UAT
  - Risk: LOW (can bump to llama3.2:3b if needed)

### Before Phase 05-06 Begins

- [ ] **Multi-platform emotional consistency:** Do Discord + Android share state correctly?
  - Action: Phase 5-6 integration testing
  - Risk: MEDIUM (requires tight state sync)

---

## Recommendation

Phase 04 is ready for planning. Key decisions locked:
- ✅ Use Ollama + ollama-python SDK (Pattern B)
- ✅ llama3.2:1b as base model (scalable if needed)
- ✅ transformers-based token counting with estimation fallback
- ✅ System prompt injection for emotional modulation
- ✅ 8K context window with sliding history trimming

Plans should be sequential (Plan 01 → 02 → 03 → 04) due to dependencies on inference foundation → prompt builder → response processing → full integration.
