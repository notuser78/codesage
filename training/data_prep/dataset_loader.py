"""
Dataset loader for training
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import structlog
from datasets import Dataset, load_dataset

logger = structlog.get_logger()


class DatasetLoader:
    """Load and prepare datasets for training"""

    def __init__(self, config: dict):
        self.config = config
        self.max_seq_length = config.get("max_seq_length", 2048)

    def load_sft_dataset(self) -> Dataset:
        """Load dataset for supervised fine-tuning"""
        datasets = []

        for source in self.config.get("sources", []):
            logger.info(f"Loading dataset: {source['name']}")

            ds = self._load_source(source)
            if ds:
                # Apply weight
                weight = source.get("weight", 1.0)
                if weight != 1.0:
                    ds = ds.shuffle(seed=42).select(range(int(len(ds) * weight)))

                datasets.append(ds)

        # Combine datasets
        if len(datasets) == 1:
            return datasets[0]

        from datasets import concatenate_datasets

        combined = concatenate_datasets(datasets)
        return combined.shuffle(seed=42)

    def load_rlhf_dataset(self) -> Dataset:
        """Load preference dataset for RLHF"""
        pref_config = self.config.get("preference_data", {})
        path = pref_config.get("path")

        if not path or not Path(path).exists():
            logger.error(f"Preference dataset not found: {path}")
            raise FileNotFoundError(f"Dataset not found: {path}")

        logger.info(f"Loading preference dataset from {path}")

        # Load JSONL file
        data = []
        with open(path, "r") as f:
            for line in f:
                data.append(json.loads(line))

        return Dataset.from_list(data)

    def _load_source(self, source: dict) -> Optional[Dataset]:
        """Load a single dataset source"""
        path = source.get("path")
        name = source.get("name")

        if not path:
            logger.warning(f"No path specified for source: {name}")
            return None

        path_obj = Path(path)

        if not path_obj.exists():
            logger.warning(f"Dataset not found: {path}")
            return None

        # Load based on file extension
        if path.endswith(".jsonl"):
            data = []
            with open(path, "r") as f:
                for line in f:
                    data.append(json.loads(line))
            return Dataset.from_list(data)

        elif path.endswith(".json"):
            with open(path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return Dataset.from_list(data)
            else:
                return Dataset.from_dict(data)

        elif path.endswith(".parquet"):
            import pandas as pd

            df = pd.read_parquet(path)
            return Dataset.from_pandas(df)

        else:
            # Try to load with HuggingFace datasets
            try:
                return load_dataset(path, split="train")
            except Exception as e:
                logger.error(f"Failed to load dataset {path}: {e}")
                return None

    def format_for_training(self, dataset: Dataset, format_type: str = "chat") -> Dataset:
        """Format dataset for training"""
        if format_type == "chat":
            return dataset.map(self._format_chat_example)
        elif format_type == "instruction":
            return dataset.map(self._format_instruction_example)
        else:
            return dataset

    def _format_chat_example(self, example: dict) -> dict:
        """Format a single example for chat training"""
        # Format: <|system|>...<|user|>...<|assistant|>...
        messages = example.get("messages", [])

        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted += f"<|{role}|>{content}"

        return {
            "text": formatted,
            "messages": messages,
        }

    def _format_instruction_example(self, example: dict) -> dict:
        """Format a single example for instruction training"""
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output = example.get("output", "")

        # Format: ### Instruction: ...\n### Input: ...\n### Response: ...
        prompt = f"### Instruction:\n{instruction}\n"
        if input_text:
            prompt += f"### Input:\n{input_text}\n"
        prompt += f"### Response:\n{output}"

        return {
            "text": prompt,
            "instruction": instruction,
            "input": input_text,
            "output": output,
        }
