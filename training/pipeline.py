"""
CodeSage Model Training Pipeline
Supports SFT (Supervised Fine-Tuning) and RLHF training
"""

import argparse
import os
import sys
from pathlib import Path

import structlog
import yaml

from data_prep.dataset_loader import DatasetLoader
from trainers.sft_trainer import SFTTrainer
from trainers.rlhf_trainer import RLHFTrainer

logger = structlog.get_logger()


def load_config(config_path: str) -> dict:
    """Load training configuration from YAML file"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def run_sft_training(config: dict):
    """Run supervised fine-tuning"""
    logger.info("Starting SFT training", config=config)

    # Load dataset
    dataset_loader = DatasetLoader(config["data"])
    train_dataset = dataset_loader.load_sft_dataset()

    # Initialize trainer
    trainer = SFTTrainer(config["training"])

    # Train
    model = trainer.train(train_dataset)

    # Save
    output_dir = config["training"].get("output_dir", "./output/sft")
    trainer.save_model(model, output_dir)

    logger.info("SFT training complete", output_dir=output_dir)

    return output_dir


def run_rlhf_training(config: dict, base_model_path: str):
    """Run RLHF training"""
    logger.info("Starting RLHF training", config=config, base_model=base_model_path)

    # Load dataset
    dataset_loader = DatasetLoader(config["data"])
    train_dataset = dataset_loader.load_rlhf_dataset()

    # Initialize trainer
    trainer = RLHFTrainer(config["training"], base_model_path)

    # Train
    model = trainer.train(train_dataset)

    # Save
    output_dir = config["training"].get("output_dir", "./output/rlhf")
    trainer.save_model(model, output_dir)

    logger.info("RLHF training complete", output_dir=output_dir)

    return output_dir


def main():
    parser = argparse.ArgumentParser(description="CodeSage Training Pipeline")
    parser.add_argument(
        "--mode", type=str, choices=["sft", "rlhf", "both"], required=True, help="Training mode"
    )
    parser.add_argument("--config", type=str, required=True, help="Path to config file")
    parser.add_argument("--output_dir", type=str, default="./output", help="Output directory")
    parser.add_argument("--base_model", type=str, help="Base model path (for RLHF)")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Update output directory
    config["training"]["output_dir"] = args.output_dir

    # Run training
    if args.mode == "sft":
        run_sft_training(config)
    elif args.mode == "rlhf":
        if not args.base_model:
            logger.error("Base model path required for RLHF training")
            sys.exit(1)
        run_rlhf_training(config, args.base_model)
    elif args.mode == "both":
        sft_output = run_sft_training(config)
        run_rlhf_training(config, sft_output)


if __name__ == "__main__":
    main()
