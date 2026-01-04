#!/usr/bin/env bash
# =============================================================================
# SOVRN Model Download Script
# Downloads and prepares the Llama 3.2 11B model for local inference
# =============================================================================

set -e

MODEL_DIR="${1:-./models}"
MODEL_NAME="llama-3.2-11b-vision-instruct"
QUANTIZATION="${2:-Q4_K_M}"

echo "🚀 SOVRN Model Downloader"
echo "========================="
echo ""

# Create models directory
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo "📁 Model directory: $(pwd)"
echo "📦 Model: $MODEL_NAME"
echo "🔧 Quantization: $QUANTIZATION"
echo ""

# Check if huggingface-cli is available
if ! command -v huggingface-cli &> /dev/null; then
    echo "⚠️  huggingface-cli not found. Installing..."
    pip install huggingface_hub[cli]
fi

# Download the quantized GGUF model
echo "📥 Downloading model..."
echo "   This may take a while depending on your connection speed."
echo ""

# Using the official Llama 3.2 GGUF quantized model
# You can change this to other quantizations:
# - Q4_K_M (recommended): ~7GB, good balance of quality and speed
# - Q5_K_M: ~8.5GB, higher quality, slightly slower
# - Q8_0: ~12GB, best quality, slowest
# - Q2_K: ~4GB, fastest, lower quality

MODEL_FILE="llama-3.2-11b-vision-instruct.${QUANTIZATION}.gguf"
HUGGINGFACE_REPO="bartowski/Llama-3.2-11B-Vision-Instruct-GGUF"

if [ -f "$MODEL_FILE" ]; then
    echo "✅ Model already exists: $MODEL_FILE"
else
    huggingface-cli download "$HUGGINGFACE_REPO" "$MODEL_FILE" --local-dir . --local-dir-use-symlinks False
    echo "✅ Model downloaded successfully!"
fi

# Verify the model file
if [ -f "$MODEL_FILE" ]; then
    MODEL_SIZE=$(du -h "$MODEL_FILE" | cut -f1)
    echo ""
    echo "📊 Model Info:"
    echo "   File: $MODEL_FILE"
    echo "   Size: $MODEL_SIZE"
else
    echo "❌ Error: Model file not found after download"
    exit 1
fi

# Create a symlink for easy reference
ln -sf "$MODEL_FILE" "model.gguf" 2>/dev/null || true

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start the inference server, run:"
echo "   docker compose up infer"
echo ""
echo "Or with llama.cpp directly:"
echo "   llama-server -m models/$MODEL_FILE --host 0.0.0.0 --port 8080"
echo ""
