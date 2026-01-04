#!/usr/bin/env python3
"""Test inference service by loading model and generating text"""

import asyncio
import sys
sys.path.insert(0, '/app')

from model_manager import model_manager
from pathlib import Path


async def test_model():
    """Test loading and running the model"""
    
    # Load the model
    print("🔧 Loading model...")
    model_path = Path("/models/qwen2-1_5b-instruct-q4_k_m.gguf")
    
    try:
        await model_manager.load_model(model_path)
        print("✅ Model loaded successfully!")
        
        # Get model info
        info = model_manager.get_model_info()
        print(f"📊 Model info: {info}")
        
        # Test a simple generation
        print("\n🤖 Testing generation...")
        prompt = "Hello! Please respond in one sentence."
        
        result = model_manager.model(prompt, max_tokens=50, temperature=0.7)
        print(f"💬 Response: {result['choices'][0]['text']}")
        
        print("\n✅ Inference test complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_model())
    sys.exit(0 if success else 1)
