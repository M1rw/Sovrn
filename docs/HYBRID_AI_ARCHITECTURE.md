# SOVRN Hybrid AI Architecture

## Overview

SOVRN implements a hybrid AI architecture that combines cloud and local AI for the best of both worlds:

- **Primary: Puter.js (Cloud)** - Free access to GPT-4o-mini, Claude, Llama, and DeepSeek models
- **Backup: Phi-3-mini (Local)** - 100% offline inference when cloud is unavailable

## Key Advantages Over Competitors

### vs MiniMax AI

| Feature | MiniMax AI | SOVRN |
|---------|-----------|-------|
| Reasoning | Single-shot | 8-phase deep thinking |
| Offline Mode | ❌ No | ✅ Yes (Phi-3-mini) |
| Free Tier | Limited | Unlimited (Puter.js) |
| Self-hosted | ❌ No | ✅ Yes |
| Open Source | ❌ No | ✅ Yes |
| Multi-model | Limited | ✅ 10+ models |

### Deep Thinking Pipeline

Unlike single-shot generation, SOVRN uses an 8-phase reasoning process:

1. **UNDERSTAND** - Parse and deeply understand user requirements
2. **RESEARCH** - Analyze best practices and successful patterns
3. **IDEATE** - Generate creative concepts and approaches
4. **ARCHITECT** - Plan page structure and user flow
5. **DESIGN** - Create comprehensive design system
6. **IMPLEMENT** - Generate production-ready code
7. **VERIFY** - Self-check for issues and quality
8. **REFINE** - Polish and improve the final output

This produces significantly higher quality websites than single-shot approaches.

## Architecture Components

### 1. Puter.js Client (`puter_client.py`)

Cloud AI integration with free model access:

```python
from app.lib.ai import PuterAI

puter = PuterAI()
response = await puter.chat(
    messages=[PuterMessage(role="user", content="Hello!")],
    model=PuterModel.GPT_4O_MINI,
    temperature=0.7,
)
```

Available models:
- `gpt-4o-mini` (default, fast)
- `gpt-4o` (quality)
- `claude-3-5-sonnet` (quality)
- `claude-3-haiku` (fast)
- `llama-3.1-405b` (powerful)
- `deepseek-reasoner` (thinking)

### 2. Phi-3 Client (`phi3_client.py`)

100% offline inference with Phi-3-mini:

```python
from app.lib.ai import Phi3LocalAI

phi3 = Phi3LocalAI()
response = await phi3.chat(
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.7,
)
```

Features:
- 4K context window
- Q4_K_M quantization (~2.4GB)
- CPU-optimized inference
- Simulated chain-of-thought

### 3. Hybrid Engine (`providers.py`)

Unified interface with automatic fallback:

```python
from app.lib.ai import get_ai_engine, AIMode

engine = await get_ai_engine()

# Automatic provider selection
response = await engine.generate(
    prompt="Create a website for a coffee shop",
    mode=AIMode.THINKING,  # Uses deep reasoning
)
```

Generation modes:
- `FAST` - Quick responses (GPT-4o-mini)
- `BALANCED` - Good quality/speed
- `QUALITY` - Best results (Claude Sonnet)
- `THINKING` - Multi-step reasoning (DeepSeek)

### 4. Deep Thinking Engine (`deep_thinking.py`)

Multi-phase reasoning for complex tasks:

```python
from app.lib.ai import DeepThinkingEngine

engine = await get_ai_engine()
thinking = DeepThinkingEngine(engine)

result = await thinking.think(
    prompt="Create a website for an artisanal coffee roastery",
)

# Access the full thinking chain
print(result.thinking_chain)
print(result.final_output)
```

## API Endpoints

### Chat Completion

```http
POST /api/v1/ai/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "provider": "auto",  // auto, puter, phi3
  "mode": "balanced",  // fast, balanced, quality, thinking
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### Website Generation

```http
POST /api/v1/ai/generate/website
Content-Type: application/json

{
  "prompt": "Create a modern coffee shop website",
  "mode": "full",  // quick or full
  "return_thinking": true
}
```

### Streaming

```http
POST /api/v1/ai/generate/website/stream
Content-Type: application/json

{
  "prompt": "Create a tech startup landing page"
}
```

Returns Server-Sent Events with progress updates.

## Frontend Integration

### React Hook

```typescript
import { useState } from 'react';

function useSOVRNAI() {
  const [loading, setLoading] = useState(false);
  
  const generate = async (prompt: string) => {
    setLoading(true);
    const res = await fetch('/api/v1/ai/generate/website', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, mode: 'full' }),
    });
    setLoading(false);
    return res.json();
  };
  
  return { generate, loading };
}
```

### Direct Puter.js (Browser)

```typescript
import { PuterAI } from '@/lib/puter-ai';

// Generate directly from browser
const result = await PuterAI.generateWebsite(
  "Create a portfolio site for a photographer"
);
```

## Model Download

Download Phi-3-mini for offline mode:

```bash
./scripts/download-phi3-model.sh
```

Or manually:

```bash
wget -O models/phi-3-mini-4k-instruct-q4.gguf \
  https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf
```

## Environment Variables

```env
# Hybrid AI Configuration
AI_PRIMARY_PROVIDER=puter      # puter, phi3, or auto
AI_ENABLE_FALLBACK=true        # Enable Phi-3 backup
AI_PRELOAD_LOCAL=false         # Preload Phi-3 on startup

# Phi-3 Configuration
MODEL_PATH=/models/phi-3-mini-4k-instruct-q4.gguf
MODEL_CONTEXT_SIZE=4096
MODEL_THREADS=4

# Generation Defaults
DEFAULT_MODE=balanced          # fast, balanced, quality, thinking
DEFAULT_TEMPERATURE=0.7
```

## Performance Comparison

Typical response times:

| Mode | Cloud (Puter) | Local (Phi-3) |
|------|---------------|---------------|
| Fast | ~1-2s | ~5-10s |
| Balanced | ~2-4s | ~10-20s |
| Quality | ~4-8s | ~20-40s |
| Thinking | ~10-30s | ~60-120s |

Website generation (full pipeline):
- Quick mode: 20-40s
- Full mode: 60-180s

## Best Practices

1. **Use AUTO provider** - Let the system choose the best option
2. **Enable fallback** - Ensure AI is always available
3. **Cache responses** - Store generated websites for reuse
4. **Stream for UX** - Use streaming for real-time feedback
5. **Monitor usage** - Track provider stats via `/api/v1/ai/status`

## Troubleshooting

### Puter.js not responding
- Check internet connection
- Verify Puter.js SDK is loaded
- Try alternative model (Claude → GPT-4o)

### Phi-3 too slow
- Increase `MODEL_THREADS`
- Reduce `MAX_TOKENS`
- Use "quick" mode

### Low quality output
- Switch to "quality" or "thinking" mode
- Add more context in prompt
- Use system prompts

## Contributing

The hybrid AI system is designed to be extensible:

1. Add new providers in `app/lib/ai/`
2. Register in `providers.py`
3. Add endpoints in `endpoints/ai.py`

Pull requests welcome!
