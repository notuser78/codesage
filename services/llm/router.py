"""
Model router for handling generation requests
Routes requests to appropriate models and handles fallbacks
"""

import time
from typing import AsyncGenerator, List, Optional

import structlog

from adapters.base_adapter import GenerationRequest, GenerationResponse
from model_loader import ModelLoader

logger = structlog.get_logger()


class ModelRouter:
    """Routes generation requests to appropriate models"""

    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader
        self.request_count = 0
        self.error_count = 0

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Route generation request to appropriate model"""
        self.request_count += 1

        start_time = time.time()

        # Select model based on request
        model_id = request.model or self.model_loader.default_model

        # Load model if not already loaded
        if model_id not in self.model_loader.loaded_models:
            success = await self.model_loader.load_model(model_id)
            if not success:
                # Fallback to default model
                logger.warning(f"Failed to load {model_id}, falling back to default")
                model_id = self.model_loader.default_model

        try:
            # Generate
            result = await self.model_loader.generate(
                prompt=request.prompt,
                model_id=model_id,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                repetition_penalty=request.repetition_penalty,
                stop_sequences=request.stop_sequences,
            )

            generation_time_ms = int((time.time() - start_time) * 1000)

            return GenerationResponse(
                text=result["text"],
                tokens_generated=result["tokens_generated"],
                generation_time_ms=generation_time_ms,
                model_used=result["model_used"],
            )

        except Exception as e:
            self.error_count += 1
            logger.error(f"Generation failed: {e}")
            raise

    async def generate_stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[str, None]:
        """Stream generation results"""
        # For now, just yield the full result
        # In a full implementation, this would yield tokens as they're generated
        response = await self.generate(request)
        yield response.text

    async def batch_generate(
        self,
        requests: List[GenerationRequest],
    ) -> List[GenerationResponse]:
        """Generate for multiple requests"""
        import asyncio

        # Process in batches
        batch_size = self.model_loader.max_batch_size
        results = []

        for i in range(0, len(requests), batch_size):
            batch = requests[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.generate(req) for req in batch],
                return_exceptions=True,
            )
            results.extend(batch_results)

        return results

    def get_stats(self) -> dict:
        """Get router statistics"""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count),
        }
