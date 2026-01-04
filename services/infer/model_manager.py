# =============================================================================
# SOVRN Inference Service - Model Manager
# =============================================================================
"""
Manages loading, caching, and lifecycle of llama.cpp models
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict
import structlog

from llama_cpp import Llama, LlamaCache

from config import settings

logger = structlog.get_logger()


class ModelManager:
    """Manages llama.cpp model lifecycle."""
    
    def __init__(self):
        self.model: Optional[Llama] = None
        self.model_path: Optional[Path] = None
        self.is_loading = False
        self._load_lock = asyncio.Lock()
        
    async def load_model(self, model_path: Optional[Path] = None) -> Llama:
        """
        Load a model file. If already loaded, return existing model.
        Thread-safe with async lock.
        """
        async with self._load_lock:
            target_path = model_path or settings.MODEL_PATH
            
            # If already loaded and same model, return it
            if self.model and self.model_path == target_path:
                logger.info("model_already_loaded", path=str(target_path))
                return self.model
            
            # Unload existing model if different
            if self.model and self.model_path != target_path:
                logger.info("unloading_previous_model", path=str(self.model_path))
                await self.unload_model()
            
            # Load new model
            logger.info(
                "loading_model",
                path=str(target_path),
                n_gpu_layers=settings.N_GPU_LAYERS,
                n_ctx=settings.CONTEXT_LENGTH,
                n_threads=settings.N_THREADS
            )
            
            try:
                # Run CPU-intensive model loading in thread pool
                self.model = await asyncio.to_thread(
                    self._load_model_sync,
                    target_path
                )
                
                self.model_path = target_path
                
                logger.info(
                    "model_loaded_successfully",
                    path=str(target_path),
                    vocab_size=self.model.n_vocab(),
                    context_length=self.model.n_ctx()
                )
                
                return self.model
                
            except Exception as e:
                logger.error(
                    "model_load_failed",
                    path=str(target_path),
                    error=str(e)
                )
                raise
    
    def _load_model_sync(self, model_path: Path) -> Llama:
        """Synchronous model loading (runs in thread pool)."""
        return Llama(
            model_path=str(model_path),
            n_ctx=settings.CONTEXT_LENGTH,
            n_batch=settings.N_BATCH,
            n_gpu_layers=settings.N_GPU_LAYERS,
            n_threads=settings.N_THREADS,
            use_mmap=settings.USE_MMAP,
            use_mlock=settings.USE_MLOCK,
            verbose=False,
            # Enable prompt caching
            cache=settings.ENABLE_PROMPT_CACHE,
        )
    
    async def unload_model(self):
        """Unload current model and free memory."""
        if self.model:
            logger.info("unloading_model", path=str(self.model_path))
            # llama-cpp-python will clean up on del
            del self.model
            self.model = None
            self.model_path = None
            
            # Force garbage collection
            import gc
            gc.collect()
    
    def get_model(self) -> Optional[Llama]:
        """Get currently loaded model (if any)."""
        return self.model
    
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.model is not None
    
    async def list_available_models(self) -> Dict[str, Path]:
        """List all available .gguf models in the models directory."""
        models = {}
        
        if settings.MODELS_DIR.exists():
            for model_file in settings.MODELS_DIR.glob("*.gguf"):
                models[model_file.stem] = model_file
        
        return models
    
    def get_model_info(self) -> Optional[Dict]:
        """Get information about currently loaded model."""
        if not self.model:
            return None
        
        return {
            "path": str(self.model_path),
            "name": self.model_path.stem if self.model_path else None,
            "vocab_size": self.model.n_vocab(),
            "context_length": self.model.n_ctx(),
            "embedding_size": self.model.n_embd(),
        }


# Global model manager instance
model_manager = ModelManager()
