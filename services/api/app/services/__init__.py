# Services module
# Avoid importing GenerationService here to prevent circular imports when agents import inference.
from app.services.inference import InferenceClient, inference_client

__all__ = ["InferenceClient", "inference_client"]
