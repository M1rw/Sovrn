# SOVRN Model Setup Guide

This directory contains the AI models used by SOVRN for website generation.

## Quick Start

### Windows
```powershell
.\scripts\download-model.ps1
```

### Linux/macOS
```bash
chmod +x scripts/download-model.sh
./scripts/download-model.sh
```

## Supported Models

SOVRN uses **Llama 3.2 11B Vision Instruct** as the default model, optimized for:
- Understanding business requirements
- Generating structured JSON outputs
- Code generation
- Cultural adaptation

### Recommended Quantizations

| Quantization | Size | RAM Required | Quality | Speed |
|--------------|------|--------------|---------|-------|
| Q2_K | ~4GB | 6GB | Lower | Fastest |
| Q4_K_M | ~7GB | 8GB | Good | Fast |
| Q5_K_M | ~8.5GB | 10GB | Better | Medium |
| Q8_0 | ~12GB | 14GB | Best | Slower |

**Recommendation**: Use `Q4_K_M` for the best balance of quality and performance on 8GB RAM systems.

## Manual Download

If the script doesn't work, you can download manually:

1. Visit: https://huggingface.co/bartowski/Llama-3.2-11B-Vision-Instruct-GGUF
2. Download your preferred quantization (e.g., `llama-3.2-11b-vision-instruct.Q4_K_M.gguf`)
3. Place it in the `models/` directory
4. Update `.env` with the model filename:
   ```
   MODEL_PATH=/models/llama-3.2-11b-vision-instruct.Q4_K_M.gguf
   ```

## Alternative Models

You can use other models compatible with llama.cpp:

### Smaller Models (for lower RAM systems)
- **Llama 3.2 3B**: ~2GB RAM, faster but lower quality
- **Phi-3 Mini**: ~2.5GB RAM, good for code generation
- **Mistral 7B**: ~5GB RAM, good general purpose

### Larger Models (for better quality)
- **Llama 3.1 70B**: ~40GB RAM, highest quality
- **Mixtral 8x7B**: ~25GB RAM, MoE architecture

To use a different model, update `MODEL_PATH` in your `.env` file.

## Inference Server Configuration

The model is served via llama.cpp's server. Configuration options in `docker-compose.yml`:

```yaml
services:
  infer:
    command: >
      --model /models/model.gguf
      --host 0.0.0.0
      --port 8080
      --ctx-size 4096        # Context window size
      --n-gpu-layers 0       # GPU layers (0 for CPU-only)
      --threads 4            # CPU threads
      --batch-size 512       # Batch size for prompt processing
```

### CPU vs GPU

By default, SOVRN runs on CPU for maximum compatibility. For GPU acceleration:

1. Install CUDA (NVIDIA) or ROCm (AMD)
2. Use the GPU-enabled llama.cpp image
3. Set `--n-gpu-layers` to the number of layers to offload

Example for NVIDIA GPU:
```yaml
services:
  infer:
    image: ghcr.io/ggerganov/llama.cpp:server-cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Troubleshooting

### Out of Memory
- Use a smaller quantization (Q4_K_M → Q2_K)
- Reduce context size (`--ctx-size 2048`)
- Close other applications

### Slow Generation
- Increase thread count (`--threads 8`)
- Use a smaller model
- Consider GPU acceleration

### Model Loading Errors
- Verify the model file isn't corrupted (re-download)
- Ensure sufficient disk space
- Check file permissions

## Performance Benchmarks

On a 4 vCPU / 8GB RAM VPS (typical $8/month Hetzner):

| Operation | Time (Q4_K_M) |
|-----------|---------------|
| Model load | ~30 seconds |
| Strategy agent | ~20-40 seconds |
| Designer agent | ~30-60 seconds |
| Engineer agent | ~60-120 seconds |
| **Total generation** | **~2-4 minutes** |

First generation after startup is slower due to model loading. Subsequent generations are faster.
