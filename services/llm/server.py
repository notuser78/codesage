"""
CodeSage LLM Service
Model serving API for code analysis and generation
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from adapters.base_adapter import GenerationRequest, GenerationResponse
from adapters.performance_adapter import PerformanceAdapter
from adapters.security_adapter import SecurityAdapter
from model_loader import ModelLoader
from router import ModelRouter

logger = structlog.get_logger()

# Global instances
model_loader: Optional[ModelLoader] = None
model_router: Optional[ModelRouter] = None
security_adapter: Optional[SecurityAdapter] = None
performance_adapter: Optional[PerformanceAdapter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global model_loader, model_router, security_adapter, performance_adapter

    logger.info("Starting LLM Service")

    # Initialize model loader
    model_loader = ModelLoader()
    await model_loader.load_default_model()

    # Initialize router
    model_router = ModelRouter(model_loader)

    # Initialize adapters
    security_adapter = SecurityAdapter(model_loader)
    performance_adapter = PerformanceAdapter(model_loader)

    logger.info("LLM Service ready")

    yield

    # Cleanup
    logger.info("Shutting down LLM Service")
    if model_loader:
        await model_loader.unload_all()


app = FastAPI(
    title="CodeSage LLM Service",
    description="Language model serving for code analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    default_model: str
    device: str


class ModelInfo(BaseModel):
    id: str
    name: str
    status: str
    loaded_at: Optional[str]
    parameters: Optional[int]
    quantization: Optional[str]


class CodeAnalysisRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50000)
    language: str
    analysis_type: str  # security, performance, explanation
    context: Optional[str] = None
    max_tokens: int = Field(default=1024, ge=1, le=4096)
    temperature: float = Field(default=0.1, ge=0, le=2)


class CodeAnalysisResponse(BaseModel):
    analysis: str
    suggestions: List[str]
    confidence: float
    model_used: str
    generation_time_ms: int


class VulnerabilityFixRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=10000)
    vulnerability_type: str
    language: str
    line_number: Optional[int] = None


class VulnerabilityFixResponse(BaseModel):
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float


class CodeCompletionRequest(BaseModel):
    prefix: str = Field(..., max_length=10000)
    suffix: Optional[str] = None
    language: str
    max_tokens: int = Field(default=256, ge=1, le=1024)
    temperature: float = Field(default=0.2, ge=0, le=2)


class EmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=100)
    model: Optional[str] = None


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        models_loaded=len(model_loader.loaded_models) if model_loader else 0,
        default_model=model_loader.default_model if model_loader else "none",
        device=model_loader.device if model_loader else "unknown",
    )


@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List available models"""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not ready")

    return [
        ModelInfo(
            id=model_id,
            name=info.get("name", model_id),
            status=info.get("status", "unknown"),
            loaded_at=info.get("loaded_at"),
            parameters=info.get("parameters"),
            quantization=info.get("quantization"),
        )
        for model_id, info in model_loader.get_model_info().items()
    ]


@app.post("/models/{model_id}/load")
async def load_model(model_id: str):
    """Load a model"""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        await model_loader.load_model(model_id)
        return {"status": "loaded", "model_id": model_id}
    except Exception as e:
        logger.error(f"Failed to load model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{model_id}/unload")
async def unload_model(model_id: str):
    """Unload a model"""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        await model_loader.unload_model(model_id)
        return {"status": "unloaded", "model_id": model_id}
    except Exception as e:
        logger.error(f"Failed to unload model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate_text(request: GenerationRequest):
    """Generate text using the loaded model"""
    if not model_router:
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = time.time()

    try:
        response = await model_router.generate(request)
        return response
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/stream")
async def generate_stream(request: GenerationRequest):
    """Stream text generation"""
    if not model_router:
        raise HTTPException(status_code=503, detail="Service not ready")

    async def stream_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in model_router.generate_stream(request):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f'data: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
    )


@app.post("/analyze/code", response_model=CodeAnalysisResponse)
async def analyze_code(request: CodeAnalysisRequest):
    """Analyze code for issues"""
    if not security_adapter or not performance_adapter:
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = time.time()

    try:
        if request.analysis_type == "security":
            result = await security_adapter.analyze(request.code, request.language)
        elif request.analysis_type == "performance":
            result = await performance_adapter.analyze(request.code, request.language)
        else:
            # General code explanation
            prompt = f"""Analyze the following {request.language} code and provide insights:

```{request.language}
{request.code}
```

Provide:
1. Brief explanation of what the code does
2. Potential issues or improvements
3. Best practices that could be applied
"""
            gen_request = GenerationRequest(
                prompt=prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            result = await model_router.generate(gen_request)

        generation_time_ms = int((time.time() - start_time) * 1000)

        return CodeAnalysisResponse(
            analysis=result.text if hasattr(result, "text") else result.get("text", ""),
            suggestions=result.suggestions if hasattr(result, "suggestions") else [],
            confidence=result.confidence if hasattr(result, "confidence") else 0.8,
            model_used=result.model_used if hasattr(result, "model_used") else "default",
            generation_time_ms=generation_time_ms,
        )

    except Exception as e:
        logger.error(f"Code analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fix/vulnerability", response_model=VulnerabilityFixResponse)
async def fix_vulnerability(request: VulnerabilityFixRequest):
    """Generate a fix for a security vulnerability"""
    if not security_adapter:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await security_adapter.generate_fix(
            code=request.code,
            vulnerability_type=request.vulnerability_type,
            language=request.language,
        )

        return VulnerabilityFixResponse(
            original_code=request.code,
            fixed_code=result.get("fixed_code", ""),
            explanation=result.get("explanation", ""),
            confidence=result.get("confidence", 0.8),
        )

    except Exception as e:
        logger.error(f"Vulnerability fix generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/complete/code")
async def complete_code(request: CodeCompletionRequest):
    """Complete code snippet"""
    if not model_router:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        # Format as FIM (Fill-In-the-Middle) if suffix provided
        if request.suffix:
            prompt = f"<fim_prefix>{request.prefix}<fim_suffix>{request.suffix}<fim_middle>"
        else:
            prompt = request.prefix

        gen_request = GenerationRequest(
            prompt=prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop_sequences=["\n\n", "\ndef ", "\nclass "],
        )

        result = await model_router.generate(gen_request)

        return {
            "completion": result.text,
            "model_used": result.model_used,
        }

    except Exception as e:
        logger.error(f"Code completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings for texts"""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        embeddings = await model_loader.create_embeddings(
            texts=request.texts,
            model_name=request.model,
        )

        return EmbeddingResponse(
            embeddings=embeddings,
            model=request.model or model_loader.embedding_model,
            dimension=len(embeddings[0]) if embeddings else 0,
        )

    except Exception as e:
        logger.error(f"Embedding creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
