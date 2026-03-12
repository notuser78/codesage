"""
Base adapter for LLM interactions
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request for text generation"""
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=0.9, ge=0, le=1)
    top_k: int = Field(default=50, ge=1, le=1000)
    repetition_penalty: float = Field(default=1.0, ge=1, le=2)
    stop_sequences: Optional[List[str]] = None


class GenerationResponse(BaseModel):
    """Response from text generation"""
    text: str
    tokens_generated: int = 0
    generation_time_ms: int = 0
    model_used: str = "default"


class BaseAdapter(ABC):
    """Base class for LLM adapters"""
    
    def __init__(self, model_loader):
        self.model_loader = model_loader
    
    @abstractmethod
    async def analyze(self, code: str, language: str) -> dict:
        """Analyze code and return results"""
        pass
    
    async def generate_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        """Generate text with system and user prompts"""
        # Format for instruction-following models
        prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt} [/INST]"
        
        from model_loader import ModelLoader
        
        result = await self.model_loader.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return result["text"]
