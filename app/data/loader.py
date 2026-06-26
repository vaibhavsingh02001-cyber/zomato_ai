"""Dataset loader for fetching the restaurant dataset."""

import json
import logging
import os
from datasets import load_dataset
from app.config import settings

logger = logging.getLogger(__name__)


class DatasetLoader:
    """Loads the Zomato restaurant recommendation dataset from Hugging Face or local fallback."""

    def __init__(self, dataset_name: str | None = None):
        self.dataset_name = dataset_name or settings.hf_dataset
        # Resolve the local fallback file path relative to this file
        self.local_fallback_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "zomato_raw_sample.json")
        )

    def load_raw_dataset(self) -> list[dict]:
        """Fetch the dataset from Hugging Face and return rows as a list of dicts.

        If loading from Hugging Face fails (e.g. offline/network issue), falls back
        to the local `data/zomato_raw_sample.json` file.
        """
        if settings.use_local_dataset:
            logger.info(f"Loading dataset from local fallback (configured default): {self.local_fallback_path}")
            return self._load_local_fallback()

        logger.info(f"Attempting to load dataset from Hugging Face: {self.dataset_name}")
        try:
            dataset = load_dataset(self.dataset_name, split="train")
            rows = [dict(row) for row in dataset]
            logger.info(f"Loaded {len(rows)} raw rows from Hugging Face dataset.")
            return rows
        except Exception as e:
            logger.warning(
                f"Failed to load dataset from Hugging Face: {e}. "
                f"Attempting to fall back to local file: {self.local_fallback_path}"
            )
            return self._load_local_fallback(e)

    def _load_local_fallback(self, original_error: Exception | None = None) -> list[dict]:
        """Helper to load local fallback dataset."""
        if not os.path.exists(self.local_fallback_path):
            msg = (
                f"Local fallback file does not exist: {self.local_fallback_path}"
            )
            logger.error(msg)
            if original_error:
                raise RuntimeError(msg) from original_error
            raise RuntimeError(msg)

        try:
            with open(self.local_fallback_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
            logger.info(
                f"Loaded {len(rows)} raw rows from local fallback dataset: {self.local_fallback_path}"
            )
            return rows
        except Exception as local_err:
            msg = f"Failed to load local fallback dataset: {local_err}"
            logger.error(msg)
            if original_error:
                raise RuntimeError(msg) from original_error
            raise RuntimeError(msg)

