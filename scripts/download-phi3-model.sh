#!/bin/bash
# =============================================================================
# SOVRN - Download Phi-3-mini Model
# =============================================================================
# Downloads the Phi-3-mini-4k-instruct quantized model for offline inference.
# This is a high-quality, efficient model that runs well on CPU.
#
# Model: microsoft/Phi-3-mini-4k-instruct (Q4_K_M quantization)
# Size: ~2.4GB
# Quality: Excellent for code generation and reasoning
# =============================================================================

set -e

MODELS_DIR="${1:-./models}"
MODEL_NAME="phi-3-mini-4k-instruct-q4.gguf"

# Hugging Face token for authenticated downloads
HF_TOKEN="${HF_TOKEN:-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}"

# Model URL (Microsoft official - this is the correct one)
MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

# Alternative from TheBloke (usually faster)
ALT_MODEL_URL="https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf"

echo "=============================================="
echo "SOVRN - Phi-3-mini Model Downloader"
echo "=============================================="
echo ""
echo "Model: $MODEL_NAME"
echo "Destination: $MODELS_DIR"
echo ""

# Create models directory
mkdir -p "$MODELS_DIR"

# Check if model already exists
if [ -f "$MODELS_DIR/$MODEL_NAME" ]; then
    echo "Model already exists at $MODELS_DIR/$MODEL_NAME"
    echo "Delete it first if you want to re-download."
    exit 0
fi

# Check for wget or curl
if command -v wget &> /dev/null; then
    echo "Downloading with wget (authenticated)..."
    wget -O "$MODELS_DIR/$MODEL_NAME" "$MODEL_URL" \
        --header="Authorization: Bearer $HF_TOKEN" \
        --show-progress \
        --progress=bar:force:noscroll
elif command -v curl &> /dev/null; then
    echo "Downloading with curl (authenticated)..."
    curl -L -o "$MODELS_DIR/$MODEL_NAME" "$MODEL_URL" \
        -H "Authorization: Bearer $HF_TOKEN" \
        --progress-bar
else
    echo "Error: Neither wget nor curl found. Please install one."
    exit 1
fi

# Verify download
if [ -f "$MODELS_DIR/$MODEL_NAME" ]; then
    SIZE=$(du -h "$MODELS_DIR/$MODEL_NAME" | cut -f1)
    echo ""
    echo "=============================================="
    echo "Download complete!"
    echo "Model: $MODELS_DIR/$MODEL_NAME"
    echo "Size: $SIZE"
    echo "=============================================="
    echo ""
    echo "The Phi-3-mini model is ready for offline inference."
    echo "SOVRN will automatically use it as a backup when cloud AI is unavailable."
else
    echo "Error: Download failed."
    exit 1
fi
