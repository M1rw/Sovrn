#!/usr/bin/env python3
from llama_cpp import Llama

print("🔧 Loading TinyLlama model...")
model = Llama(
    model_path="/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    n_ctx=2048,
    n_threads=2,
    n_gpu_layers=0,
    verbose=False
)

print("✅ Model loaded successfully!")

print("\n🤖 Testing generation...")
result = model("Hello, my name is", max_tokens=30, temperature=0.7)
print(f"💬 Response: {result['choices'][0]['text']}")

print("\n✅ Inference test complete!")
