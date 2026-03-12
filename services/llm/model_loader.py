"""
Model loader for managing LLM models
Handles loading, unloading, and inference
"""

import os
import time
from typing import Dict, List, Optional

import structlog
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    pipeline,
)

logger = structlog.get_logger()


class ModelLoader:
    """Manages loading and inference of language models"""
    
    def __init__(self):
        self.model_path = os.getenv("MODEL_PATH", "/models")
        self.default_model = os.getenv("DEFAULT_MODEL", "codellama-7b")
        self.device = self._get_device()
        self.max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "4"))
        self.max_sequence_length = int(os.getenv("MAX_SEQUENCE_LENGTH", "4096"))
        
        self.loaded_models: Dict[str, dict] = {}
        self.tokenizers: Dict[str, AutoTokenizer] = {}
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.embedding_pipeline = None
        
        logger.info(
            "ModelLoader initialized",
            device=self.device,
            default_model=self.default_model,
        )
    
    def _get_device(self) -> str:
        """Determine the best available device"""
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA available: {device_count} device(s), using {device_name}")
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("MPS available")
            return "mps"
        else:
            logger.info("Using CPU")
            return "cpu"
    
    async def load_default_model(self):
        """Load the default model"""
        await self.load_model(self.default_model)
    
    async def load_model(
        self,
        model_id: str,
        quantization: Optional[str] = None,
    ) -> bool:
        """Load a model by ID"""
        if model_id in self.loaded_models:
            logger.info(f"Model {model_id} already loaded")
            return True
        
        logger.info(f"Loading model: {model_id}")
        start_time = time.time()
        
        try:
            # Map model IDs to HuggingFace model names
            model_map = {
                "codellama-7b": "codellama/CodeLlama-7b-Instruct-hf",
                "codellama-13b": "codellama/CodeLlama-13b-Instruct-hf",
                "codellama-34b": "codellama/CodeLlama-34b-Instruct-hf",
                "starcoder": "bigcode/starcoder",
                "starcoder2": "bigcode/starcoder2-7b",
                "deepseek-coder": "deepseek-ai/deepseek-coder-6.7b-instruct",
            }
            
            model_name = model_map.get(model_id, model_id)
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.model_path,
                trust_remote_code=True,
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            self.tokenizers[model_id] = tokenizer
            
            # Load model with appropriate settings
            load_kwargs = {
                "cache_dir": self.model_path,
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
            }
            
            # Add quantization if specified
            if quantization == "4bit" and self.device == "cuda":
                load_kwargs["load_in_4bit"] = True
                load_kwargs["device_map"] = "auto"
            elif quantization == "8bit" and self.device == "cuda":
                load_kwargs["load_in_8bit"] = True
                load_kwargs["device_map"] = "auto"
            
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                **load_kwargs,
            )
            
            if self.device != "cuda" or not quantization:
                model = model.to(self.device)
            
            model.eval()
            
            # Store model info
            self.loaded_models[model_id] = {
                "model": model,
                "name": model_name,
                "status": "loaded",
                "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "parameters": self._count_parameters(model),
                "quantization": quantization,
            }
            
            load_time = time.time() - start_time
            logger.info(
                f"Model {model_id} loaded successfully",
                load_time_seconds=load_time,
                parameters=self.loaded_models[model_id]["parameters"],
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            self.loaded_models[model_id] = {
                "status": "error",
                "error": str(e),
            }
            return False
    
    async def unload_model(self, model_id: str) -> bool:
        """Unload a model to free memory"""
        if model_id not in self.loaded_models:
            logger.warning(f"Model {model_id} not loaded")
            return False
        
        logger.info(f"Unloading model: {model_id}")
        
        try:
            # Remove from memory
            if "model" in self.loaded_models[model_id]:
                del self.loaded_models[model_id]["model"]
            
            if model_id in self.tokenizers:
                del self.tokenizers[model_id]
            
            del self.loaded_models[model_id]
            
            # Force garbage collection
            import gc
            gc.collect()
            
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            logger.info(f"Model {model_id} unloaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload model {model_id}: {e}")
            return False
    
    async def unload_all(self):
        """Unload all models"""
        for model_id in list(self.loaded_models.keys()):
            await self.unload_model(model_id)
    
    def get_model(self, model_id: Optional[str] = None):
        """Get a loaded model"""
        model_id = model_id or self.default_model
        
        if model_id not in self.loaded_models:
            raise ValueError(f"Model {model_id} not loaded")
        
        model_info = self.loaded_models[model_id]
        if "model" not in model_info:
            raise ValueError(f"Model {model_id} not properly loaded")
        
        return model_info["model"], self.tokenizers.get(model_id)
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        return {
            model_id: {
                k: v for k, v in info.items()
                if k != "model"  # Don't include the actual model object
            }
            for model_id, info in self.loaded_models.items()
        }
    
    def _count_parameters(self, model) -> int:
        """Count model parameters"""
        return sum(p.numel() for p in model.parameters())
    
    async def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.0,
        stop_sequences: Optional[List[str]] = None,
    ) -> Dict:
        """Generate text using a model"""
        model, tokenizer = self.get_model(model_id)
        
        if tokenizer is None:
            raise ValueError("Tokenizer not available")
        
        # Tokenize input
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_sequence_length - max_tokens,
        )
        
        if self.device != "cuda":
            inputs = inputs.to(self.device)
        
        # Generate
        start_time = time.time()
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                do_sample=temperature > 0,
            )
        
        generation_time = time.time() - start_time
        
        # Decode output
        input_length = inputs.input_ids.shape[1]
        generated_tokens = outputs[0][input_length:]
        generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # Apply stop sequences
        if stop_sequences:
            for stop_seq in stop_sequences:
                if stop_seq in generated_text:
                    generated_text = generated_text[:generated_text.index(stop_seq)]
        
        return {
            "text": generated_text,
            "tokens_generated": len(generated_tokens),
            "generation_time_ms": int(generation_time * 1000),
            "model_used": model_id or self.default_model,
        }
    
    async def create_embeddings(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
    ) -> List[List[float]]:
        """Create embeddings for texts"""
        if self.embedding_pipeline is None:
            from sentence_transformers import SentenceTransformer
            
            model_name = model_name or self.embedding_model
            logger.info(f"Loading embedding model: {model_name}")
            
            self.embedding_pipeline = SentenceTransformer(
                model_name,
                cache_folder=self.model_path,
                device=self.device,
            )
        
        embeddings = self.embedding_pipeline.encode(
            texts,
            convert_to_tensor=False,
            show_progress_bar=False,
        )
        
        return embeddings.tolist()
