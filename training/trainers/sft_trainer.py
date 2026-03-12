"""
Supervised Fine-Tuning Trainer
"""

import os
from typing import Optional

import structlog
import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer as TrlSFTTrainer

logger = structlog.get_logger()


class SFTTrainer:
    """Supervised Fine-Tuning Trainer"""
    
    def __init__(self, config: dict):
        self.config = config
        self.model_config = config.get('model', {})
        self.peft_config = config.get('peft', {})
        self.training_args = self._create_training_args()
    
    def _create_training_args(self) -> TrainingArguments:
        """Create training arguments"""
        output_dir = self.config.get('output_dir', './output/sft')
        
        return TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=self.config.get('num_train_epochs', 3),
            per_device_train_batch_size=self.config.get('per_device_train_batch_size', 4),
            per_device_eval_batch_size=self.config.get('per_device_eval_batch_size', 4),
            gradient_accumulation_steps=self.config.get('gradient_accumulation_steps', 4),
            learning_rate=self.config.get('learning_rate', 2e-4),
            weight_decay=self.config.get('weight_decay', 0.001),
            warmup_ratio=self.config.get('warmup_ratio', 0.03),
            lr_scheduler_type=self.config.get('lr_scheduler_type', 'cosine'),
            logging_steps=self.config.get('logging_steps', 10),
            eval_steps=self.config.get('eval_steps', 100),
            save_steps=self.config.get('save_steps', 500),
            evaluation_strategy=self.config.get('evaluation_strategy', 'steps'),
            save_strategy=self.config.get('save_strategy', 'steps'),
            load_best_model_at_end=self.config.get('load_best_model_at_end', True),
            metric_for_best_model=self.config.get('metric_for_best_model', 'eval_loss'),
            fp16=self.config.get('fp16', False),
            bf16=self.config.get('bf16', True),
            gradient_checkpointing=self.config.get('gradient_checkpointing', True),
            group_by_length=self.config.get('group_by_length', True),
            report_to="wandb" if self.config.get('wandb', {}).get('enabled') else None,
        )
    
    def _load_model_and_tokenizer(self):
        """Load model and tokenizer"""
        model_name = self.model_config.get('base_model', 'codellama/CodeLlama-7b-hf')
        
        logger.info(f"Loading model: {model_name}")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=self.model_config.get('trust_remote_code', True),
        )
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        
        # Quantization config
        quantization_config = None
        quant_config = self.model_config.get('quantization', {})
        
        if quant_config.get('enabled', False):
            quant_method = quant_config.get('method', '4bit')
            
            if quant_method == '4bit':
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=getattr(
                        torch, quant_config.get('compute_dtype', 'bfloat16')
                    ),
                    bnb_4bit_quant_type=quant_config.get('quant_type', 'nf4'),
                    bnb_4bit_use_double_quant=quant_config.get('use_nested_quant', True),
                )
            elif quant_method == '8bit':
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        
        # Load model
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            torch_dtype=getattr(
                torch, self.model_config.get('torch_dtype', 'bfloat16')
            ),
            trust_remote_code=self.model_config.get('trust_remote_code', True),
            device_map="auto",
        )
        
        # Prepare model for training
        if quantization_config:
            model = prepare_model_for_kbit_training(model)
        
        # Apply PEFT/LoRA
        if self.peft_config.get('enabled', True):
            lora_config = LoraConfig(
                r=self.peft_config.get('r', 64),
                lora_alpha=self.peft_config.get('lora_alpha', 16),
                lora_dropout=self.peft_config.get('lora_dropout', 0.1),
                bias=self.peft_config.get('bias', 'none'),
                task_type=self.peft_config.get('task_type', 'CAUSAL_LM'),
                target_modules=self.peft_config.get('target_modules', [
                    'q_proj', 'k_proj', 'v_proj', 'o_proj'
                ]),
            )
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
        
        return model, tokenizer
    
    def train(self, dataset):
        """Run training"""
        model, tokenizer = self._load_model_and_tokenizer()
        
        logger.info("Starting training...")
        
        # Create trainer
        trainer = TrlSFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            args=self.training_args,
            max_seq_length=self.config.get('max_seq_length', 2048),
        )
        
        # Train
        trainer.train()
        
        return model
    
    def save_model(self, model, output_dir: str):
        """Save the trained model"""
        logger.info(f"Saving model to {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Save model
        model.save_pretrained(output_dir)
        
        # Save tokenizer
        _, tokenizer = self._load_model_and_tokenizer()
        tokenizer.save_pretrained(output_dir)
        
        logger.info("Model saved successfully")
