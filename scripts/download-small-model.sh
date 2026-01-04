#!/usr/bin/env bash
# Download a small model for testing (Qwen2 1.5B - only ~1GB)
set -e

MODEL_DIR="/workspaces/Sovrn/models"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo "📥 Downloading Qwen2-1.5B-Instruct (Q4_K_M) - Small model for testing..."
echo "   Size: ~1GB, Fast download and inference"
echo ""

# Check if model exists
if [ -f "qwen2-1_5b-instruct-q4_k_m.gguf" ]; then
    echo "✅ Model already exists!"
else
    # Download using wget (faster than huggingface-cli for single files)
    wget -O qwen2-1_5b-instruct-q4_k_m.gguf \
        "https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF/resolve/main/qwen2-1_5b-instruct-q4_k_m.gguf" \
        --progress=bar:force 2>&1
    
    echo ""
    echo "✅ Model downloaded successfully!"
fi

# Verify
if [ -f "qwen2-1_5b-instruct-q4_k_m.gguf" ]; then
    SIZE=$(du -h qwen2-1_5b-instruct-q4_k_m.gguf | cut -f1)
    echo "📊 Model: qwen2-1_5b-instruct-q4_k_m.gguf"
    echo "📦 Size: $SIZE"
    echo ""
    echo "✨ Ready for inference!"
else
    echo "❌ Download failed"
    exit 1
fi
