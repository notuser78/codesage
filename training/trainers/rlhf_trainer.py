"""
RLHF Trainer using PPO
"""

import os
from typing import Optional

import structlog
import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)
from trl import PPOConfig, PPOTrainer, AutoModelForCausalLMWithValueHead

logger = structlog.get_logger()


class RLHFTrainer:
    """RLHF Trainer using PPO"""

    def __init__(self, config: dict, base_model_path: str):
        self.config = config
        self.base_model_path = base_model_path
        self.ppo_config = config.get("ppo", {})

    def _create_ppo_config(self) -> PPOConfig:
        """Create PPO configuration"""
        return PPOConfig(
            model_name=self.base_model_path,
            learning_rate=self.ppo_config.get("learning_rate", 1e-5),
            batch_size=self.ppo_config.get("batch_size", 4),
            mini_batch_size=self.ppo_config.get("mini_batch_size", 1),
            gradient_accumulation_steps=self.ppo_config.get("gradient_accumulation_steps", 4),
            ppo_epochs=self.ppo_config.get("ppo_epochs", 4),
            init_kl_coef=self.ppo_config.get("init_kl_coef", 0.2),
            target_kl=self.ppo_config.get("target_kl", 0.1),
            adap_kl_ctrl=self.ppo_config.get("adap_kl_ctrl", True),
            cliprange=self.ppo_config.get("cliprange", 0.2),
            cliprange_value=self.ppo_config.get("cliprange_value", 0.2),
            vf_coef=self.ppo_config.get("vf_coef", 0.1),
            gamma=self.ppo_config.get("gamma", 0.99),
            lam=self.ppo_config.get("lam", 0.95),
            log_with="wandb" if self.config.get("wandb", {}).get("enabled") else None,
        )

    def _load_models(self):
        """Load policy and reference models"""
        logger.info(f"Loading base model from {self.base_model_path}")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.base_model_path)
        tokenizer.pad_token = tokenizer.eos_token

        # Load policy model with value head
        model = AutoModelForCausalLMWithValueHead.from_pretrained(
            self.base_model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )

        # Load reference model (frozen)
        ref_model = None
        if self.config.get("use_reference_model", True):
            ref_model = AutoModelForCausalLM.from_pretrained(
                self.base_model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
            )
            for param in ref_model.parameters():
                param.requires_grad = False

        return model, ref_model, tokenizer

    def _build_reward_model(self):
        """Build or load reward model"""
        reward_config = self.config.get("reward_model", {})
        model_name = reward_config.get("base_model", self.base_model_path)

        logger.info(f"Loading reward model from {model_name}")

        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=1,  # Regression for reward
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )

        return model

    def train(self, dataset):
        """Run RLHF training"""
        model, ref_model, tokenizer = self._load_models()
        reward_model = self._build_reward_model()

        ppo_config = self._create_ppo_config()

        logger.info("Starting RLHF training...")

        # Create PPO trainer
        trainer = PPOTrainer(
            config=ppo_config,
            model=model,
            ref_model=ref_model,
            tokenizer=tokenizer,
            dataset=dataset,
        )

        # Training loop
        generation_config = self.config.get("generation", {})

        for epoch in range(self.config.get("num_epochs", 1)):
            for batch in trainer.dataloader:
                # Generate responses
                queries = batch["query"]

                response_tensors = trainer.generate(
                    queries,
                    max_new_tokens=generation_config.get("max_new_tokens", 512),
                    temperature=generation_config.get("temperature", 0.7),
                    top_p=generation_config.get("top_p", 0.9),
                    do_sample=generation_config.get("do_sample", True),
                )

                # Compute rewards
                responses = [
                    tokenizer.decode(r, skip_special_tokens=True) for r in response_tensors
                ]

                # Get rewards from reward model
                rewards = self._compute_rewards(
                    reward_model,
                    tokenizer,
                    queries,
                    responses,
                )

                # Update policy
                stats = trainer.step(queries, response_tensors, rewards)

                logger.info(f"Training stats: {stats}")

        return model

    def _compute_rewards(self, reward_model, tokenizer, queries, responses):
        """Compute rewards using reward model"""
        rewards = []

        for query, response in zip(queries, responses):
            # Combine query and response
            text = query + response

            # Tokenize
            inputs = tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            ).to(reward_model.device)

            # Get reward score
            with torch.no_grad():
                outputs = reward_model(**inputs)
                reward = outputs.logits[0].item()

            rewards.append(torch.tensor(reward))

        return rewards

    def save_model(self, model, output_dir: str):
        """Save the trained model"""
        logger.info(f"Saving model to {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        # Save model
        model.save_pretrained(output_dir)

        # Save tokenizer
        _, _, tokenizer = self._load_models()
        tokenizer.save_pretrained(output_dir)

        logger.info("Model saved successfully")
